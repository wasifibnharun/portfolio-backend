from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


MAX_IMAGE_SIZE = 2 * 1024 * 1024
MAX_RESUME_SIZE = 5 * 1024 * 1024


validate_image_extension = FileExtensionValidator(
    allowed_extensions=["jpg", "jpeg", "png", "webp"],
    message="Only JPG, JPEG, PNG, and WEBP images are allowed.",
)

validate_pdf_extension = FileExtensionValidator(
    allowed_extensions=["pdf"],
    message="The resume must be a PDF file.",
)


def validate_image_size(file):
    if file.size > MAX_IMAGE_SIZE:
        raise ValidationError("Image size must not exceed 2 MB.")


def validate_resume_size(file):
    if file.size > MAX_RESUME_SIZE:
        raise ValidationError("Resume size must not exceed 5 MB.")