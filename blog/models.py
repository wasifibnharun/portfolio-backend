import math
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.html import strip_tags

from portfolio.models import (
    TimeStampedModel,
    generate_unique_slug,
)
from portfolio.validators import (
    validate_image_extension,
    validate_image_size,
)


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Post(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    title = models.CharField(
        max_length=250,
        validators=[
            MinLengthValidator(
                5,
                message="Post title must contain at least 5 characters.",
            ),
        ],
    )
    slug = models.SlugField(
        max_length=270,
        unique=True,
        blank=True,
    )
    excerpt = models.CharField(max_length=300)
    content = models.TextField(
        help_text="Post content is stored as Markdown.",
    )
    cover_image = models.ImageField(
        upload_to="blog/covers/",
        validators=[
            validate_image_extension,
            validate_image_size,
        ],
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="posts",
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="posts",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="blog_posts",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    views_count = models.PositiveBigIntegerField(
        default=0,
        editable=False,
    )
    reading_time = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Estimated reading time in minutes.",
    )
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def clean(self):
        super().clean()
        errors = {}

        if (
            self.status == self.Status.PUBLISHED
            and len(self.content.strip()) < 100
        ):
            errors["content"] = (
                "A published post must contain at least 100 characters."
            )

        if self.status == self.Status.PUBLISHED and not self.category_id:
            errors["category"] = (
                "A published post must have a category."
            )

        if self.author_id and not self.author.is_superuser:
            errors["author"] = (
                "The post author must be the site owner."
            )

        if errors:
            raise ValidationError(errors)

    def calculate_reading_time(self):
        plain_content = strip_tags(self.content)
        words = re.findall(r"\b[\w'-]+\b", plain_content)
        word_count = len(words)

        if word_count == 0:
            return 0

        return max(1, math.ceil(word_count / 200))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)

        self.reading_time = self.calculate_reading_time()

        previous_published_at = None

        if self.pk:
            previous_published_at = (
                Post.objects
                .filter(pk=self.pk)
                .values_list("published_at", flat=True)
                .first()
            )

        if previous_published_at is not None:
            # Once assigned, the original publication time never changes.
            self.published_at = previous_published_at
        elif self.status == self.Status.PUBLISHED:
            self.published_at = timezone.now()
        else:
            self.published_at = None

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class PostLike(TimeStampedModel):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    visitor_id = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = (("post", "visitor_id"),)

    def __str__(self):
        return f"{self.visitor_id} liked {self.post.title}"


class Comment(TimeStampedModel):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    name = models.CharField(
        max_length=100,
        validators=[
            MinLengthValidator(
                2,
                message="Name must contain at least 2 characters.",
            ),
        ],
    )
    email = models.EmailField()
    website = models.URLField(blank=True)
    content = models.TextField(
        validators=[
            MinLengthValidator(
                5,
                message="Comment must contain at least 5 characters.",
            ),
            MaxLengthValidator(
                1000,
                message="Comment must not exceed 1000 characters.",
            ),
        ],
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        errors = {}

        if self.parent_id:
            if self.parent_id == self.pk:
                errors["parent"] = (
                    "A comment cannot be its own parent."
                )
            elif self.parent.post_id != self.post_id:
                errors["parent"] = (
                    "A reply must belong to the same post."
                )
            elif self.parent.parent_id is not None:
                errors["parent"] = (
                    "Only one level of comment replies is allowed."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Comment by {self.name} on {self.post.title}"