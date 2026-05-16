from pydantic import BaseModel, Field
from typing import List, Optional

class MenuItem(BaseModel):
    item_name: str = Field(description="Name of the dish")
    translated_item_name: Optional[str] = Field(None, description="English translation if original is not English")
    description: Optional[str] = Field(None, description="Description of the dish")
    translated_description: Optional[str] = Field(None, description="English translation of the description")
    category: Optional[str] = Field(None, description="e.g., Appetizer, Main Course, Dessert")
    price: Optional[str] = Field(None, description="The price as a string")
    currency: Optional[str] = Field(None, description="Currency code, e.g., USD, EUR, INR")
    calories: Optional[str] = Field(None, description="Caloric information")
    allergens: List[str] = Field(default_factory=list, description="List of allergens")
    dietary_tags: List[str] = Field(default_factory=list, description="Dietary tags like Vegan, Gluten-Free")
    image_path: Optional[str] = Field(None, description="Local path to the cropped dish image")

class MenuSchema(BaseModel):
    restaurant_name: Optional[str] = Field(None, description="Name of the restaurant")
    menu_language: Optional[str] = Field(None, description="Detected language of the original menu")
    menu_items: List[MenuItem] = Field(default_factory=list, description="List of menu items")


class ExtractionResponse(BaseModel):
    success: bool
    data: Optional[MenuSchema] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

    
