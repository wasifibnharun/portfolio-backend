from django.contrib.auth import get_user_model
from rest_framework import serializers

from portfolio.serializers import (
    IMAGE_CONTENT_TYPES,
    AbsoluteImageField,
)
from portfolio.validators import (
    validate_image_extension,
    validate_image_size,
)

from .models import Category, Post, Tag

User = get_user_model()


class AuthorSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
        )
        read_only_fields = fields


class CategorySerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(
        read_only=True,
        default=0,
    )

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "posts_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "posts_count",
            "created_at",
            "updated_at",
        )


class TagSerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(
        read_only=True,
        default=0,
    )

    class Meta:
        model = Tag
        fields = (
            "id",
            "name",
            "slug",
            "posts_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "posts_count",
            "created_at",
            "updated_at",
        )


class RelatedPostSerializer(serializers.ModelSerializer):
    cover_image = AbsoluteImageField(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Post
        fields = (
            "title",
            "slug",
            "excerpt",
            "cover_image",
            "category",
            "published_at",
            "reading_time",
        )


class PostListSerializer(serializers.ModelSerializer):
    cover_image = AbsoluteImageField(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author = AuthorSummarySerializer(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "cover_image",
            "category",
            "tags",
            "author",
            "status",
            "published_at",
            "views_count",
            "reading_time",
            "is_featured",
            "likes_count",
            "comments_count",
            "created_at",
            "updated_at",
        )


class PostDetailSerializer(PostListSerializer):
    is_liked = serializers.SerializerMethodField()
    related_posts = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "cover_image",
            "category",
            "tags",
            "author",
            "status",
            "published_at",
            "views_count",
            "reading_time",
            "is_featured",
            "likes_count",
            "comments_count",
            "is_liked",
            "related_posts",
            "created_at",
            "updated_at",
        )

    def get_is_liked(self, obj):
        request = self.context.get("request")

        if request is None:
            return False

        visitor_id = request.headers.get(
            "X-Visitor-Id",
            "",
        ).strip()

        if not visitor_id:
            return False

        return obj.likes.filter(
            visitor_id=visitor_id
        ).exists()

    def get_related_posts(self, obj):
        related = (
            Post.objects.filter(
                status=Post.Status.PUBLISHED,
                category=obj.category,
            )
            .exclude(pk=obj.pk)
            .select_related("category")
            .order_by("-published_at")[:3]
        )

        return RelatedPostSerializer(
            related,
            many=True,
            context=self.context,
        ).data


class PostWriteSerializer(serializers.ModelSerializer):
    cover_image = AbsoluteImageField(
        validators=[
            validate_image_extension,
            validate_image_size,
        ],
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        allow_empty=False,
        error_messages={
            "empty": "Select at least one tag.",
        },
    )
    author = AuthorSummarySerializer(read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "cover_image",
            "category",
            "tags",
            "author",
            "status",
            "published_at",
            "views_count",
            "reading_time",
            "is_featured",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "author",
            "published_at",
            "views_count",
            "reading_time",
            "created_at",
            "updated_at",
        )

    def validate_title(self, value):
        value = value.strip()

        if len(value) < 5:
            raise serializers.ValidationError(
                "Post title must contain at least 5 characters."
            )

        return value

    def validate_cover_image(self, file):
        content_type = getattr(file, "content_type", "").lower()

        if content_type and content_type not in IMAGE_CONTENT_TYPES:
            raise serializers.ValidationError(
                "Only JPG, JPEG, PNG, and WEBP images are allowed."
            )

        return file

    def validate(self, attrs):
        instance = self.instance

        status_value = attrs.get(
            "status",
            getattr(instance, "status", Post.Status.DRAFT),
        )
        content = attrs.get(
            "content",
            getattr(instance, "content", ""),
        )
        category = attrs.get(
            "category",
            getattr(instance, "category", None),
        )

        errors = {}

        if (
            status_value == Post.Status.PUBLISHED
            and len(content.strip()) < 100
        ):
            errors["content"] = (
                "A published post must contain at least 100 characters."
            )

        if (
            status_value == Post.Status.PUBLISHED
            and category is None
        ):
            errors["category"] = (
                "A published post must have a category."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs