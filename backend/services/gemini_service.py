# backend/services/gemini_service.py
import google.generativeai as genai
from backend.config import config
from backend.models.schemas import MenuSchema
import json
from typing import Union
import time
from PIL import Image  # Add this import

class GeminiService:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.MODEL_NAME)

    def extract_menu_from_text(self, text: str) -> MenuSchema:
        """Extract menu data from text using Gemini"""
        prompt = f"""
        You are an expert at extracting structured data from restaurant menus.

        Analyze the following menu text and extract ALL menu items with their details.

        Menu Text:
        {text}

        Instructions:
        1. Extract every single dish/item from the menu
        2. For each item, provide:
           - item_name: The name of the dish
           - translated_item_name: If menu is not in English, provide English translation
           - description: Description of the dish (if available)
           - translated_description: English translation of description (if needed)
           - category: Type of dish (Appetizer, Main Course, Dessert, Drink, etc.)
           - price: The price as a string (just the number)
           - currency: Currency code (USD, EUR, GBP, INR, etc.)
           - calories: Calorie information if mentioned
           - allergens: List of allergens (e.g., ["Nuts", "Dairy", "Gluten"])
           - dietary_tags: List of dietary tags (e.g., ["Vegan", "Gluten-Free", "Spicy", "Jain"])

        3. If information is not available, use null for strings, empty list for arrays
        4. Detect the menu language from the text
        5. Try to identify the restaurant name if present

        Return ONLY valid JSON matching this exact structure:
        {{
            "restaurant_name": "string or null",
            "menu_language": "string or null",
            "menu_items": [
                {{
                    "item_name": "string",
                    "translated_item_name": "string or null",
                    "description": "string or null",
                    "translated_description": "string or null",
                    "category": "string or null",
                    "price": "string or null",
                    "currency": "string or null",
                    "calories": "string or null",
                    "allergens": [],
                    "dietary_tags": []
                }}
            ]
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            # Clean the response (remove markdown code blocks if present)
            cleaned_response = self._clean_json_response(response.text)
            data = json.loads(cleaned_response)
            return MenuSchema(**data)
        except Exception as e:
            print(f"Error extracting menu from text: {e}")
            raise

    def extract_menu_from_image(self, image_path: str) -> MenuSchema:
        """Extract menu data from image using Gemini's vision capabilities"""
        try:
            # Open the image
            img = Image.open(image_path)

            prompt = """
            Analyze this restaurant menu image and extract ALL menu items.

            For each dish, extract:
            - Item name
            - Description (if any)
            - Category (Appetizer, Main Course, Dessert, etc.)
            - Price
            - Currency symbol/type
            - Calories (if mentioned)
            - Allergens (if mentioned)
            - Dietary tags (Vegan, Gluten-Free, Spicy, Jain, etc.)

            Also identify:
            - Restaurant name (if visible)
            - Menu language

            If the menu is not in English, provide English translations in the translated_* fields.

            Return JSON in this exact format:
            {
                "restaurant_name": "name or null",
                "menu_language": "language code or null",
                "menu_items": [
                    {
                        "item_name": "name",
                        "translated_item_name": "translation or null",
                        "description": "description or null",
                        "translated_description": "translation or null",
                        "category": "category or null",
                        "price": "price string or null",
                        "currency": "currency code or null",
                        "calories": "calories or null",
                        "allergens": [],
                        "dietary_tags": []
                    }
                ]
            }

            Extract ALL visible items accurately. Be thorough and extract every dish you see.
            """

            # Generate content with image
            response = self.model.generate_content([prompt, img])

            # Clean and parse the response
            cleaned_response = self._clean_json_response(response.text)
            data = json.loads(cleaned_response)
            return MenuSchema(**data)

        except FileNotFoundError:
            raise Exception(f"Image file not found: {image_path}")
        except Exception as e:
            print(f"Error extracting menu from image: {e}")
            raise

    def _clean_json_response(self, response_text: str) -> str:
        """Clean Gemini response to extract valid JSON"""
        # Remove markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return response_text.strip()