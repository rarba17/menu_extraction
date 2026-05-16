# backend/services/image_processor.py
import cv2
import numpy as np
from PIL import Image
import os
import uuid
from backend.config import config

class ImageProcessor:
    @staticmethod
    def preprocess_image(image_path: str) -> np.ndarray:
        """Preprocess image for better OCR/extraction"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply threshold to get binary image
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Denoise
        denoised = cv2.medianBlur(thresh, 3)

        return denoised

    @staticmethod
    def detect_and_crop_images(image_path: str) -> list:
        """
        Detect potential food images in the menu and crop them.
        Returns list of saved image paths.
        """
        img = cv2.imread(image_path)
        if img is None:
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Use edge detection to find potential image regions
        edges = cv2.Canny(gray, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cropped_images = []
        img_height, img_width = img.shape[:2]

        for i, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)

            # Filter based on size (potential images are usually larger than 100x100)
            if w > 100 and h > 100 and w < img_width * 0.8 and h < img_height * 0.5:
                # Add some padding
                padding = 10
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(img_width - x, w + 2*padding)
                h = min(img_height - y, h + 2*padding)

                # Crop the region
                cropped = img[y:y+h, x:x+w]

                # Save cropped image
                filename = f"cropped_food_{uuid.uuid4().hex[:8]}.jpg"
                save_path = os.path.join(config.OUTPUT_DIR, filename)
                cv2.imwrite(save_path, cropped)
                cropped_images.append(save_path)

        return cropped_images

    @staticmethod
    def image_to_bytes(image_path: str) -> bytes:
        """Convert image to bytes for Gemini API"""
        with open(image_path, 'rb') as f:
            return f.read()