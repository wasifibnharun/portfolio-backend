from django.utils import timezone
from rest_framework import serializers

from .models import (
    Education,
    Experience,
    Profile,
    Skill,
)
from .validators import (
    validate_image_extension,
    validate_image_size,
    validate_pdf_extension,
    validate_resume_size,
)

IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


class AbsoluteImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None

        request = self.context.get("request")
        url = value.url

        if request:
            return request.build_absolute_uri(url)

        return url


class AbsoluteFileField(serializers.FileField):
    def to_representation(self, value):
        if not value:
            return None

        request = self.context.get("request")
        url = value.url

        if request:
            return request.build_absolute_uri(url)

        return url


class ProfileSerializer(serializers.ModelSerializer):
    avatar = AbsoluteImageField(
        validators=[
            validate_image_extension,
            validate_image_size,
        ],
    )
    resume = AbsoluteFileField(
        validators=[
            validate_pdf_extension,
            validate_resume_size,
        ],
    )

    class Meta:
        model = Profile
        fields = (
            "id",
            "full_name",
            "headline",
            "bio",
            "email",
            "phone",
            "location",
            "avatar",
            "resume",
            "github_url",
            "linkedin_url",
            "x_url",
            "website_url",
            "years_of_experience",
            "is_available_for_hire",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate_avatar(self, file):
        content_type = getattr(file, "content_type", "").lower()

        if content_type and content_type not in IMAGE_CONTENT_TYPES:
            raise serializers.ValidationError(
                "Only JPG, JPEG, PNG, and WEBP images are allowed."
            )

        return file

    def validate_resume(self, file):
        content_type = getattr(file, "content_type", "").lower()

        if content_type and content_type not in PDF_CONTENT_TYPES:
            raise serializers.ValidationError(
                "The resume must be a PDF file."
            )

        return file


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = (
            "id",
            "name",
            "category",
            "proficiency",
            "icon",
            "display_order",
            "is_featured",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate_proficiency(self, value):
        if not 1 <= value <= 100:
            raise serializers.ValidationError(
                "Proficiency must be between 1 and 100."
            )

        return value


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = (
            "id",
            "company",
            "role",
            "employment_type",
            "location",
            "start_date",
            "end_date",
            "is_current",
            "description",
            "company_url",
            "display_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        instance = self.instance

        start_date = attrs.get(
            "start_date",
            getattr(instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(instance, "end_date", None),
        )
        is_current = attrs.get(
            "is_current",
            getattr(instance, "is_current", False),
        )

        errors = {}

        if start_date and start_date > timezone.localdate():
            errors["start_date"] = (
                "Start date cannot be in the future."
            )

        if is_current and end_date:
            errors["end_date"] = (
                "End date must be empty for a current position."
            )

        if not is_current and not end_date:
            errors["end_date"] = (
                "End date is required when the position is not current."
            )

        if (
            start_date
            and end_date
            and end_date <= start_date
        ):
            errors["end_date"] = (
                "End date must be after start date."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = (
            "id",
            "institution",
            "degree",
            "field_of_study",
            "start_year",
            "end_year",
            "grade",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        instance = self.instance

        start_year = attrs.get(
            "start_year",
            getattr(instance, "start_year", None),
        )
        end_year = attrs.get(
            "end_year",
            getattr(instance, "end_year", None),
        )

        if (
            start_year is not None
            and end_year is not None
            and end_year < start_year
        ):
            raise serializers.ValidationError(
                {
                    "end_year": (
                        "End year cannot be before start year."
                    )
                }
            )

        return attrs