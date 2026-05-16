# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    MODEL_NAME = "gemini-1.5-pro-latest"  # or "gemini-1.5-flash" for faster/lighter
    OUTPUT_DIR = "outputs"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

config = Config()

# Create output directory if it doesn't exist
os.makedirs(config.OUTPUT_DIR, exist_ok=True)