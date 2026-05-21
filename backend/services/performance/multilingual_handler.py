# backend/services/performance/multilingual_handler.py
"""
Multilingual menu handler — uses OpenAI GPT-4o for vision + translation.
"""

import base64
import json
import logging
from typing import Dict, List

from openai import OpenAI

from backend.config import config

logger = logging.getLogger(__name__)


class MultilingualMenuHandler:
    """Handle multilingual menus using OpenAI Vision — no OCR required."""

    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.vision_model = config.OPENAI_VISION_MODEL
        self.language_cache: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    async def detect_language(self, text: str) -> Dict:
        """Detect menu language using AI."""
        if text in self.language_cache:
            return self.language_cache[text]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a language detection expert. Return ONLY valid JSON.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Analyze this restaurant menu text and return:\n"
                        f"1. Primary language (ISO 639-1 code)\n"
                        f"2. Confidence score (0-1)\n"
                        f"3. Secondary languages if any\n\n"
                        f"Menu text sample: {text[:500]}\n\n"
                        f'Return JSON: {{"primary": "en", "confidence": 0.95, "secondary": []}}'
                    ),
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=256,
            temperature=0.1,
        )

        result = json.loads(response.choices[0].message.content)
        self.language_cache[text] = result
        return result

    # ------------------------------------------------------------------
    # Batch translation
    # ------------------------------------------------------------------

    async def translate_menu_items(
        self, items: List[Dict], target_lang: str = "en"
    ) -> List[Dict]:
        """Translate menu items while preserving structure."""
        translated_items = []

        batch_size = 10
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            batch_text = "\n".join(
                f"{idx}. {item.get('item_name', '')} | {item.get('description', '')}"
                for idx, item in enumerate(batch, start=1)
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate menu items. Return ONLY a JSON array. "
                            "Keep prices, numbers, and formatting unchanged."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Translate these menu items to {target_lang}.\n\n"
                            f"Items:\n{batch_text}\n\n"
                            f"Return JSON array:\n"
                            f'[{{"translated_name": "...", "translated_description": "..."}}, ...]'
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                max_tokens=config.OPENAI_MAX_TOKENS,
                temperature=0.2,
            )

            raw = json.loads(response.choices[0].message.content)
            # The model may wrap the array in an object — handle both shapes
            translations = raw if isinstance(raw, list) else raw.get("translations", raw.get("items", []))

            for item, translation in zip(batch, translations):
                item["translated_item_name"] = translation.get("translated_name")
                item["translated_description"] = translation.get("translated_description")
                translated_items.append(item)

        return translated_items

    # ------------------------------------------------------------------
    # Core: multilingual extraction from image
    # ------------------------------------------------------------------

    async def extract_multilingual_menu(self, image_path: str) -> Dict:
        """
        Extract menu with language detection and translation.

        Pipeline:
          1. Send image to GPT-4o Vision → extract raw text in original language
          2. Detect language from extracted text
          3. Re-prompt with language context → structured JSON + translations
        """

        base64_image = self._encode_image(image_path)
        image_payload = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
                "detail": "high",
            },
        }

        # Step 1: Extract raw text in original language
        step1_response = self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract ALL text from this restaurant menu in its "
                                "original language. Do NOT translate yet. Just extract "
                                "exactly what you see. Return the extracted text as a "
                                "single string preserving the layout."
                            ),
                        },
                        image_payload,
                    ],
                }
            ],
            max_tokens=config.OPENAI_MAX_TOKENS,
            temperature=0.1,
        )
        original_text = step1_response.choices[0].message.content

        # Step 2: Detect language
        language_info = await self.detect_language(original_text)

        # Step 3: Extract structured data with language context
        step3_response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at extracting structured data from "
                        "restaurant menus. Return ONLY valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Menu language: {language_info['primary']}\n"
                        f"Extract structured menu data from this text.\n\n"
                        f"Original text:\n{original_text}\n\n"
                        f"Requirements:\n"
                        f"1. Keep original text in 'item_name' and 'description'\n"
                        f"2. Provide English translations in 'translated_item_name' "
                        f"and 'translated_description'\n"
                        f"3. If menu is already in English, translated_* fields can "
                        f"be same as original\n\n"
                        f"Return JSON with structure:\n"
                        f'{{\n'
                        f'  "restaurant_name": "...",\n'
                        f'  "menu_language": "{language_info["primary"]}",\n'
                        f'  "menu_items": [\n'
                        f'    {{\n'
                        f'      "item_name": "original name",\n'
                        f'      "translated_item_name": "english name",\n'
                        f'      "description": "original description",\n'
                        f'      "translated_description": "english description",\n'
                        f'      "category": "...",\n'
                        f'      "price": "...",\n'
                        f'      "currency": "...",\n'
                        f'      "calories": "...",\n'
                        f'      "allergens": [],\n'
                        f'      "dietary_tags": []\n'
                        f'    }}\n'
                        f'  ]\n'
                        f'}}'
                    ),
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=config.OPENAI_MAX_TOKENS,
            temperature=0.2,
        )

        return json.loads(step3_response.choices[0].message.content)

    # ------------------------------------------------------------------
    # Non-Latin script handling
    # ------------------------------------------------------------------

    async def handle_script_menus(
        self, image_path: str, script_type: str = "auto"
    ) -> Dict:
        """
        Handle non-Latin scripts (Chinese, Arabic, Hindi, etc.)
        GPT-4o excels at reading these scripts without OCR.
        """
        base64_image = self._encode_image(image_path)

        response = self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract menu data and return ONLY valid JSON.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"This menu is in a non-Latin script (possibly {script_type}).\n\n"
                                f"Extract the menu data following these rules:\n"
                                f"1. Keep original script in 'item_name'\n"
                                f"2. Provide Romanized/transliterated version if possible\n"
                                f"3. Provide English translation\n"
                                f"4. Maintain all numeric values (prices, calories)\n\n"
                                f"Return structured JSON with these fields."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=config.OPENAI_MAX_TOKENS,
            temperature=0.2,
        )

        return json.loads(response.choices[0].message.content)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """Read an image file and return its base64-encoded string."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")