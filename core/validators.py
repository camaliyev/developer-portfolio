"""Upload validators shared by models that accept user files."""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PDF_BYTES = 10 * 1024 * 1024

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]

validate_image_extension = FileExtensionValidator(IMAGE_EXTENSIONS)
validate_pdf_extension = FileExtensionValidator(["pdf"])


@deconstructible
class MaxFileSizeValidator:
    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes

    def __call__(self, file):
        if file.size > self.max_bytes:
            limit_mb = self.max_bytes / (1024 * 1024)
            raise ValidationError(f"File is too large. The maximum size is {limit_mb:.0f} MB.")

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and other.max_bytes == self.max_bytes


def validate_pdf_signature(file):
    """Reject files that are named .pdf but are not PDF documents."""
    position = file.tell() if hasattr(file, "tell") else 0
    try:
        file.seek(0)
        header = file.read(5)
    finally:
        file.seek(position)
    if header != b"%PDF-":
        raise ValidationError("The uploaded file is not a valid PDF document.")


IMAGE_VALIDATORS = [validate_image_extension, MaxFileSizeValidator(MAX_IMAGE_BYTES)]
PDF_VALIDATORS = [validate_pdf_extension, MaxFileSizeValidator(MAX_PDF_BYTES), validate_pdf_signature]
