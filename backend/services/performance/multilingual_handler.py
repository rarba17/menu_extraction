# backend/services/performance/multilingual_handler.py
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai
from backend.config import config
from PIL import Image
import json
import logging

logger = logging.getLogger(__name__)

class MultilingualMenuHandler:
    """Handle multilingual menus using AI without OCR"""

    def __init__(self):
        self.model = genai.GenerativeModel(config.MODEL_NAME)
        self.language_cache = {}

    async def detect_language(self, text: str) -> Dict:
        """Detect menu language using AI"""
        if text in self.language_cache:
            return self.language_cache[text]

        prompt = f"""
        Analyze this restaurant menu text and return:
        1. Primary language of the menu (ISO 639-1 code)
        2. Confidence score (0-1)
        3. Secondary languages if any

        Menu text sample: {text[:500]}

        Return JSON: {{"primary": "en", "confidence": 0.95, "secondary": []}}
        """

        response = self.model.generate_content(prompt)
        result = json.loads(self._clean_json_response(response.text))
        self.language_cache[text] = result
        return result

    async def translate_menu_items(self, items: List[Dict], target_lang: str = "en") -> List[Dict]:
        """Translate menu items while preserving structure"""
        translated_items = []

        # Batch translation for efficiency
        batch_size = 10
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]

            batch_text = "\n".join([
                f"{idx}. {item.get('item_name', '')} | {item.get('description', '')}"
                for idx, item in enumerate(batch, start=1)
            ])

            prompt = f"""
            Translate these menu items from their original language to {target_lang}.
            Preserve the structure and keep prices, numbers unchanged.

            Items:
            {batch_text}

            Return JSON array with translations:
            [
                {{"translated_name": "...", "translated_description": "..."}},
                ...
            ]
            """

            response = self.model.generate_content(prompt)
            translations = json.loads(self._clean_json_response(response.text))

            for item, translation in zip(batch, translations):
                item['translated_item_name'] = translation.get('translated_name')
                item['translated_description'] = translation.get('translated_description')
                translated_items.append(item)

        return translated_items

    async def extract_multilingual_menu(self, image_path: str) -> Dict:
        """Extract menu with language detection and translation"""

        # Step 1: Extract text in original language using PIL Image
        img = Image.open(image_path)

        extraction_prompt = """
        Extract ALL text from this restaurant menu in its original language.
        Do NOT translate yet. Just extract exactly what you see.

        Return the extracted text as a single string preserving the layout.
        """

        response = self.model.generate_content([extraction_prompt, img])
        original_text = response.text

        # Step 2: Detect language
        language_info = await self.detect_language(original_text)

        # Step 3: Extract structured data with language context
        structured_prompt = f"""
        Menu language: {language_info['primary']}
        Extract structured menu data from this text.

        Original text:
        {original_text}

        Requirements:
        1. Keep original text in 'item_name' and 'description'
        2. Provide English translations in 'translated_item_name' and 'translated_description'
        3. If menu is already in English, 'translated_*' fields can be same as original

        Return JSON with structure:
        {{
            "restaurant_name": "...",
            "menu_language": "{language_info['primary']}",
            "menu_items": [
                {{
                    "item_name": "original name",
                    "translated_item_name": "english name",
                    "description": "original description",
                    "translated_description": "english description",
                    "category": "...",
                    "price": "...",
                    "currency": "...",
                    "calories": "...",
                    "allergens": [],
                    "dietary_tags": []
                }}
            ]
        }}
        """

        response = self.model.generate_content(structured_prompt)
        return json.loads(self._clean_json_response(response.text))

    async def handle_script_menus(self, image_path: str, script_type: str = "auto") -> Dict:
        """
        Handle non-Latin scripts (Chinese, Arabic, Hindi, etc.)
        Gemini excels at reading these scripts without OCR
        """
        script_prompt = f"""
        This menu is in a non-Latin script (possibly {script_type}).

        Extract the menu data following these rules:
        1. Keep original script in 'item_name'
        2. Provide Romanized/transliterated version if possible
        3. Provide English translation
        4. Maintain all numeric values (prices, calories)

        Return structured JSON with these fields.
        """

        img = Image.open(image_path)

        response = self.model.generate_content([script_prompt, img])
        return json.loads(self._clean_json_response(response.text))

    @staticmethod
    def _clean_json_response(response_text: str) -> str:
        """Strip markdown code fences that Gemini sometimes wraps around JSON"""
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        return response_text.strip()