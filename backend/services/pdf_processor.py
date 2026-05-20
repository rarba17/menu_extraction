# backend/services/pdf_processor.py
import pypdf
from pdf2image import convert_from_path
import os
import tempfile
from PIL import Image

class PDFProcessor:
    @staticmethod
    def is_valid_pdf(file_path: str) -> bool:
        """Check if file is a valid PDF"""
        try:
            with open(file_path, 'rb') as file:
                # Check PDF header
                header = file.read(5)
                return header == b'%PDF-'
        except Exception:
            return False

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Extract text from PDF file with validation"""
        # First, validate it's a real PDF
        if not PDFProcessor.is_valid_pdf(pdf_path):
            raise ValueError("File is not a valid PDF document")

        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)

                # Check if PDF has any pages
                if len(pdf_reader.pages) == 0:
                    raise ValueError("PDF has no pages")

                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += f"Page {page_num + 1}:\n{page_text}\n\n"

            return text if text.strip() else None

        except pypdf.errors.PdfStreamError as e:
            print(f"PDF stream error: {e}")
            raise ValueError("PDF appears to be corrupted or invalid")
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            raise

    @staticmethod
    def extract_images_from_pdf(pdf_path: str) -> list:
        """Convert PDF pages to images for processing"""
        # Validate PDF first
        if not PDFProcessor.is_valid_pdf(pdf_path):
            raise ValueError("File is not a valid PDF document")

        images = []
        temp_dir = tempfile.mkdtemp()

        try:
            # Convert PDF pages to images with error handling
            pages = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=5)  # Limit to first 5 pages

            if not pages:
                raise ValueError("Could not extract any pages from PDF")

            for i, page in enumerate(pages):
                image_path = os.path.join(temp_dir, f"page_{i+1}.jpg")
                page.save(image_path, 'JPEG', quality=85)
                images.append(image_path)

            return images

        except Exception as e:
            print(f"Error extracting images from PDF: {e}")
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise