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

from .models import Category, Comment, Post, Tag

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

class CommentReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            "id",
            "name",
            "website",
            "content",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PublicCommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            "id",
            "name",
            "website",
            "content",
            "created_at",
            "updated_at",
            "replies",
        )
        read_only_fields = fields

    def get_replies(self, obj):
        approved_replies = obj.replies.filter(
            is_approved=True
        ).order_by("-created_at")

        return CommentReplySerializer(
            approved_replies,
            many=True,
            context=self.context,
        ).data


class CommentCreateSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Comment.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Comment
        fields = (
            "name",
            "email",
            "website",
            "content",
            "parent",
        )

    def validate_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Name must contain at least 2 characters."
            )

        return value

    def validate_content(self, value):
        value = value.strip()

        if len(value) < 5:
            raise serializers.ValidationError(
                "Comment must contain at least 5 characters."
            )

        if len(value) > 1000:
            raise serializers.ValidationError(
                "Comment must not exceed 1000 characters."
            )

        return value

    def validate_parent(self, parent):
        if parent is None:
            return parent

        post = self.context["post"]

        if parent.post_id != post.pk:
            raise serializers.ValidationError(
                "The parent comment belongs to another post."
            )

        if not parent.is_approved:
            raise serializers.ValidationError(
                "Replies can only be added to approved comments."
            )

        if parent.parent_id is not None:
            raise serializers.ValidationError(
                "Only one level of comment replies is allowed."
            )

        return parent

    def create(self, validated_data):
        return Comment.objects.create(
            post=self.context["post"],
            is_approved=False,
            **validated_data,
        )


class CommentPostSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = (
            "title",
            "slug",
        )
        read_only_fields = fields


class CommentModerationSerializer(serializers.ModelSerializer):
    post = CommentPostSummarySerializer(read_only=True)
    parent = serializers.IntegerField(
        source="parent_id",
        read_only=True,
    )

    class Meta:
        model = Comment
        fields = (
            "id",
            "post",
            "name",
            "email",
            "website",
            "content",
            "parent",
            "is_approved",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "post",
            "name",
            "email",
            "website",
            "content",
            "parent",
            "created_at",
            "updated_at",
        )