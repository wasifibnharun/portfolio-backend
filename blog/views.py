from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.response import Response

from .filters import PostFilter
from .models import Category, Post, Tag
from .pagination import PostPagination
from .serializers import (
    CategorySerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
    TagSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    filter_backends = []
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return Category.objects.annotate(
            posts_count=Count(
                "posts",
                filter=Q(
                    posts__status=Post.Status.PUBLISHED
                ),
                distinct=True,
            )
        ).order_by("name")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "This category cannot be deleted because "
                        "it is used by one or more posts."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    filter_backends = []
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return Tag.objects.annotate(
            posts_count=Count(
                "posts",
                filter=Q(
                    posts__status=Post.Status.PUBLISHED
                ),
                distinct=True,
            )
        ).order_by("name")


class PostViewSet(viewsets.ModelViewSet):
    pagination_class = PostPagination
    lookup_field = "slug"

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = PostFilter
    search_fields = [
        "title",
        "excerpt",
        "content",
    ]
    ordering_fields = [
        "published_at",
        "views_count",
        "likes_count",
        "title",
    ]
    ordering = ["-published_at"]
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        queryset = (
            Post.objects
            .select_related(
                "category",
                "author",
            )
            .prefetch_related("tags")
            .annotate(
                likes_count=Count(
                    "likes",
                    distinct=True,
                ),
                comments_count=Count(
                    "comments",
                    filter=Q(comments__is_approved=True),
                    distinct=True,
                ),
            )
        )

        user = self.request.user
        is_owner = bool(
            user.is_authenticated
            and user.is_superuser
        )
        action = getattr(self, "action", None)

        if not is_owner:
            return queryset.filter(
                status=Post.Status.PUBLISHED
            )

        if action == "list":
            requested_status = self.request.query_params.get(
                "status"
            )

            if not requested_status:
                return queryset.filter(
                    status=Post.Status.PUBLISHED
                )

            requested_status = requested_status.upper()

            if requested_status == "ALL":
                return queryset

            valid_statuses = {
                value
                for value, label in Post.Status.choices
            }

            if requested_status not in valid_statuses:
                raise ValidationError(
                    {
                        "status": (
                            "Use DRAFT, PUBLISHED, or all."
                        )
                    }
                )

            return queryset.filter(status=requested_status)

        # The owner can retrieve, edit, or delete drafts by slug.
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer

        if self.action == "retrieve":
            return PostDetailSerializer

        return PostWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)