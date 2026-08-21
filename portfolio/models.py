from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import slugify

from .validators import (
    validate_image_extension,
    validate_image_size,
    validate_pdf_extension,
    validate_resume_size,
)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    class Meta:
        abstract = True


def generate_unique_slug(instance, source_value):
    """
    Generate a unique slug without changing an existing object's URL.
    """
    slug_field = instance._meta.get_field("slug")
    max_length = slug_field.max_length

    base_slug = slugify(source_value)[:max_length] or "item"
    candidate = base_slug
    counter = 2

    queryset = instance.__class__.objects.exclude(pk=instance.pk)

    while queryset.filter(slug=candidate).exists():
        suffix = f"-{counter}"
        trimmed_base = base_slug[: max_length - len(suffix)]
        candidate = f"{trimmed_base}{suffix}"
        counter += 1

    return candidate


class Profile(TimeStampedModel):
    full_name = models.CharField(max_length=150)
    headline = models.CharField(max_length=200)
    bio = models.TextField()
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    location = models.CharField(max_length=150)

    avatar = models.ImageField(
        upload_to="profile/avatar/",
        validators=[
            validate_image_extension,
            validate_image_size,
        ],
    )
    resume = models.FileField(
        upload_to="profile/resume/",
        validators=[
            validate_pdf_extension,
            validate_resume_size,
        ],
    )

    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    x_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)

    years_of_experience = models.PositiveIntegerField(default=0)
    is_available_for_hire = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Owner profile"
        verbose_name_plural = "Owner profile"

    def clean(self):
        super().clean()

        if Profile.objects.exclude(pk=self.pk).exists():
            raise ValidationError(
                "Only one profile can exist for this website."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        return cls.objects.first()

    def __str__(self):
        return self.full_name


class Skill(TimeStampedModel):
    class Category(models.TextChoices):
        FRONTEND = "FRONTEND", "Frontend"
        BACKEND = "BACKEND", "Backend"
        DATABASE = "DATABASE", "Database"
        DEVOPS = "DEVOPS", "DevOps"
        TOOLS = "TOOLS", "Tools"
        SOFT_SKILL = "SOFT_SKILL", "Soft skill"

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )
    proficiency = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                1,
                message="Proficiency must be at least 1.",
            ),
            MaxValueValidator(
                100,
                message="Proficiency must not exceed 100.",
            ),
        ],
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional icon name, for example: python.",
    )
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(proficiency__gte=1)
                & Q(proficiency__lte=100),
                name="skill_proficiency_between_1_and_100",
            ),
        ]

    def __str__(self):
        return self.name


class Experience(TimeStampedModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full-time"
        PART_TIME = "PART_TIME", "Part-time"
        INTERNSHIP = "INTERNSHIP", "Internship"
        FREELANCE = "FREELANCE", "Freelance"
        CONTRACT = "CONTRACT", "Contract"

    company = models.CharField(max_length=150)
    role = models.CharField(max_length=150)
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
    )
    location = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField()
    company_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "display_order"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(is_current=True, end_date__isnull=True)
                    | Q(is_current=False, end_date__isnull=False)
                ),
                name="experience_current_end_date_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(end_date__isnull=True)
                    | Q(end_date__gt=F("start_date"))
                ),
                name="experience_end_after_start",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.start_date and self.start_date > timezone.localdate():
            errors["start_date"] = (
                "Start date cannot be in the future."
            )

        if self.is_current and self.end_date:
            errors["end_date"] = (
                "End date must be empty for a current position."
            )

        if not self.is_current and not self.end_date:
            errors["end_date"] = (
                "End date is required when the position is not current."
            )

        if (
            self.start_date
            and self.end_date
            and self.end_date <= self.start_date
        ):
            errors["end_date"] = (
                "End date must be after start date."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.role} at {self.company}"


class Education(TimeStampedModel):
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150)
    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    grade = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_year"]

    def clean(self):
        super().clean()

        if (
            self.end_year is not None
            and self.end_year < self.start_year
        ):
            raise ValidationError(
                {
                    "end_year": (
                        "End year cannot be before start year."
                    )
                }
            )

    def __str__(self):
        return f"{self.degree} — {self.institution}"


class Project(TimeStampedModel):
    class Category(models.TextChoices):
        WEB = "WEB", "Web"
        MOBILE = "MOBILE", "Mobile"
        API = "API", "API"
        ML = "ML", "Machine learning"
        OTHER = "OTHER", "Other"

    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
    )
    summary = models.CharField(max_length=200)
    description = models.TextField()
    cover_image = models.ImageField(
        upload_to="projects/covers/",
        validators=[
            validate_image_extension,
            validate_image_size,
        ],
    )
    tech_stack = models.ManyToManyField(
        Skill,
        related_name="projects",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )
    live_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    completed_date = models.DateField()
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "-completed_date"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~Q(live_url="")
                    | ~Q(github_url="")
                ),
                name="project_requires_live_or_github_url",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.live_url and not self.github_url:
            raise ValidationError(
                {
                    "live_url": (
                        "Provide at least one live URL or GitHub URL."
                    ),
                    "github_url": (
                        "Provide at least one live URL or GitHub URL."
                    ),
                }
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ContactMessage(TimeStampedModel):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"