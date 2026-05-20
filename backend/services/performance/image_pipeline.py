# backend/services/performance/image_pipeline.py
import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ImagePipeline:
    """Optimized image preprocessing without OCR"""

    @staticmethod
    def smart_resize(image_path: str, target_size_mb: float = 0.5) -> str:
        """
        Intelligently resize images to reduce API costs while preserving text readability
        Gemini needs just enough resolution to read text, not full 4K images
        """
        img = cv2.imread(image_path)
        if img is None:
            return image_path

        height, width = img.shape[:2]
        original_size_mb = (height * width * 3) / (1024 * 1024)

        # Calculate optimal dimensions
        if original_size_mb > target_size_mb:
            scale_factor = (target_size_mb / original_size_mb) ** 0.5
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)

            # Ensure minimum resolution for text readability
            min_dimension = 800
            if max(new_width, new_height) < min_dimension:
                scale = min_dimension / max(new_width, new_height)
                new_width = int(new_width * scale)
                new_height = int(new_height * scale)

            # Resize with different algorithms based on content
            if original_size_mb > 5:  # Very large image
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            else:
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

        # Save optimized image
        output_path = image_path.replace('.', '_optimized.')
        cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 85])

        logger.info(f"Resized image from {original_size_mb:.2f}MB to {target_size_mb:.2f}MB")
        return output_path

    @staticmethod
    def auto_orient(image_path: str) -> str:
        """Auto-rotate images based on EXIF data"""
        try:
            img = Image.open(image_path)

            # Handle EXIF orientation
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif:
                    orientation = exif.get(0x0112, 1)
                    rotate_map = {
                        3: Image.ROTATE_180,
                        6: Image.ROTATE_270,
                        8: Image.ROTATE_90
                    }
                    if orientation in rotate_map:
                        img = img.transpose(rotate_map[orientation])
                        img.save(image_path)
                        logger.info(f"Auto-rotated image with orientation {orientation}")
        except Exception as e:
            logger.warning(f"Auto-orientation failed: {e}")

        return image_path

    @staticmethod
    def enhance_contrast(image_path: str) -> str:
        """Enhance contrast for better text visibility"""
        img = cv2.imread(image_path)
        if img is None:
            return image_path

        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)

        # Merge back
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        cv2.imwrite(image_path, enhanced)
        return image_path