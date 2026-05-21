# backend/services/openai_service.py
"""
OpenAI-powered menu extraction service.
Drop-in replacement for GeminiService — same public interface.
"""

import base64
import json
import logging
import time
from typing import Optional

from openai import OpenAI
from PIL import Image

from backend.config import config
from backend.models.schemas import MenuSchema

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON schema passed to OpenAI function-calling to guarantee structure
# ---------------------------------------------------------------------------
MENU_FUNCTION_SCHEMA = {
    "name": "extract_menu",
    "description": "Return structured menu data extracted from a restaurant menu.",
    "parameters": {
        "type": "object",
        "properties": {
            "restaurant_name": {
                "type": ["string", "null"],
                "description": "Name of the restaurant if visible"
            },
            "menu_language": {
                "type": ["string", "null"],
                "description": "ISO 639-1 language code of the menu"
            },
            "menu_items": {
                "type": "array",
                "description": "All extracted menu items",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string"},
                        "translated_item_name": {"type": ["string", "null"]},
                        "description": {"type": ["string", "null"]},
                        "translated_description": {"type": ["string", "null"]},
                        "category": {"type": ["string", "null"]},
                        "price": {"type": ["string", "null"]},
                        "currency": {"type": ["string", "null"]},
                        "calories": {"type": ["string", "null"]},
                        "allergens": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "dietary_tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["item_name"]
                }
            }
        },
        "required": ["restaurant_name", "menu_language", "menu_items"]
    }
}


class OpenAIService:
    """
    Extracts structured menu data using OpenAI's Chat Completions API.

    Supports:
      • Text-based extraction  (GPT-4o / GPT-4o-mini)
      • Vision-based extraction (GPT-4o with base64 images)
      • Exponential-backoff retries
      • Guaranteed JSON via function-calling
    """

    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or environment variables."
            )
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.vision_model = config.OPENAI_VISION_MODEL
        self.max_tokens = config.OPENAI_MAX_TOKENS
        self.temperature = config.OPENAI_TEMPERATURE
        self.max_retries = 3

    # ------------------------------------------------------------------
    # Public API  (same signatures as GeminiService)
    # ------------------------------------------------------------------

    def extract_menu_from_text(self, text: str) -> MenuSchema:
        """Extract menu data from plain text using GPT with function calling."""

        system_msg = (
            "You are an expert at extracting structured data from restaurant menus. "
            "Extract every single dish/item. For non-English menus, provide English "
            "translations in the translated_* fields. Use null for missing strings "
            "and empty arrays where no data is available."
        )

        user_msg = (
            f"Analyze the following menu text and extract ALL menu items with their "
            f"details (name, description, category, price, currency, calories, "
            f"allergens, dietary tags). Detect the menu language and restaurant name.\n\n"
            f"Menu Text:\n{text}"
        )

        response = self._call_with_retry(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            use_function_calling=True,
        )

        data = self._parse_function_call(response)
        return MenuSchema(**data)

    def extract_menu_from_image(self, image_path: str) -> MenuSchema:
        """Extract menu data from an image using GPT-4o Vision."""

        try:
            base64_image = self._encode_image(image_path)
        except FileNotFoundError:
            raise Exception(f"Image file not found: {image_path}")

        system_msg = (
            "You are an expert at extracting structured data from restaurant menu images. "
            "Extract every visible dish accurately. For non-English menus, provide English "
            "translations. Use null for missing strings and empty arrays where no data exists."
        )

        user_content = [
            {
                "type": "text",
                "text": (
                    "Analyze this restaurant menu image and extract ALL menu items. "
                    "For each dish extract: item name, description, category "
                    "(Appetizer / Main Course / Dessert / Drink / etc.), price, "
                    "currency, calories, allergens, and dietary tags. "
                    "Also identify the restaurant name and menu language."
                ),
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "high",
                },
            },
        ]

        response = self._call_with_retry(
            model=self.vision_model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content},
            ],
            use_function_calling=True,
        )

        data = self._parse_function_call(response)
        return MenuSchema(**data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_with_retry(
        self,
        model: str,
        messages: list,
        use_function_calling: bool = False,
        max_retries: Optional[int] = None,
    ):
        """
        Call the OpenAI API with exponential backoff.
        Returns the raw ChatCompletion response object.
        """
        retries = max_retries or self.max_retries

        for attempt in range(retries):
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                }

                if use_function_calling:
                    kwargs["tools"] = [
                        {"type": "function", "function": MENU_FUNCTION_SCHEMA}
                    ]
                    kwargs["tool_choice"] = {
                        "type": "function",
                        "function": {"name": "extract_menu"},
                    }

                response = self.client.chat.completions.create(**kwargs)
                return response

            except Exception as e:
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    f"OpenAI API call failed (attempt {attempt + 1}/{retries}): {e}. "
                    f"Retrying in {wait}s..."
                )
                if attempt == retries - 1:
                    logger.error("Max retries exceeded for OpenAI API call.")
                    raise
                time.sleep(wait)

    @staticmethod
    def _parse_function_call(response) -> dict:
        """
        Extract the JSON arguments from a function-call response.
        Falls back to parsing the plain message content if no tool call exists.
        Raises a clear error if the response was truncated by the token limit.
        """
        choice = response.choices[0]

        # Guard: detect truncated output before attempting JSON parse
        if choice.finish_reason == "length":
            raise Exception(
                "OpenAI response was truncated (hit max_tokens limit). "
                "Increase OPENAI_MAX_TOKENS in your .env file or environment."
            )

        # Path 1: function / tool call
        if choice.message.tool_calls:
            raw = choice.message.tool_calls[0].function.arguments
            return json.loads(raw)

        # Path 2: plain content (fallback)
        content = choice.message.content or ""
        cleaned = OpenAIService._clean_json_response(content)
        return json.loads(cleaned)

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """Read an image file and return its base64-encoded string."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _clean_json_response(response_text: str) -> str:
        """Strip markdown code fences that LLMs sometimes wrap around JSON."""
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        return response_text.strip()
