# backend/utils/file_utils.py
import magic  # Add to requirements.txt: python-magic
import os

def validate_file_type(file_path: str) -> dict:
    """
    Validate file type and return details
    """
    mime = magic.from_file(file_path, mime=True)
    extension = os.path.splitext(file_path)[1].lower()

    valid_pdf = mime == 'application/pdf' or extension == '.pdf'
    valid_image = mime.startswith('image/') or extension in ['.jpg', '.jpeg', '.png']

    return {
        'is_valid': valid_pdf or valid_image,
        'mime_type': mime,
        'extension': extension,
        'type': 'pdf' if valid_pdf else 'image' if valid_image else 'unknown'
    }