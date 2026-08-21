from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    filters,
    generics,
    mixins,
    status,
    viewsets,
)
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from accounts.permissions import IsOwner
from config.throttles import IPScopedRateThrottle

from .filters import CommentModerationFilter, PostFilter
from .models import Category, Comment, Post, PostLike, Tag
from .pagination import CommentPagination, PostPagination
from .serializers import (
    CategorySerializer,
    CommentCreateSerializer,
    CommentModerationSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
    PublicCommentSerializer,
    TagSerializer,
)
from .services import record_post_view


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

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()

        incremented = record_post_view(post, request)

        if incremented:
            post.refresh_from_db(fields=["views_count"])

        serializer = self.get_serializer(post)
        return Response(serializer.data)

def get_client_ip(request):
    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


class PostLikeToggleView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [
        AnonRateThrottle,
        IPScopedRateThrottle,
    ]
    throttle_scope = "like"

    def post(self, request, slug, *args, **kwargs):
        visitor_id = request.headers.get(
            "X-Visitor-Id",
            "",
        ).strip()

        if not visitor_id:
            return Response(
                {
                    "detail": (
                        "The X-Visitor-Id header is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(visitor_id) > 64:
            return Response(
                {
                    "detail": (
                        "X-Visitor-Id must not exceed "
                        "64 characters."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            post = get_object_or_404(
                Post.objects.select_for_update(),
                slug=slug,
                status=Post.Status.PUBLISHED,
            )

            like, created = PostLike.objects.get_or_create(
                post=post,
                visitor_id=visitor_id,
                defaults={
                    "ip_address": get_client_ip(request),
                },
            )

            if created:
                liked = True
            else:
                like.delete()
                liked = False

            likes_count = PostLike.objects.filter(
                post=post
            ).count()

        return Response(
            {
                "liked": liked,
                "likes_count": likes_count,
            },
            status=status.HTTP_200_OK,
        )


class PostCommentsView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [
        AnonRateThrottle,
        IPScopedRateThrottle,
    ]
    pagination_class = CommentPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CommentCreateSerializer

        return PublicCommentSerializer

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "comment"
        else:
            self.throttle_scope = None

        return super().get_throttles()

    def get_post(self):
        return get_object_or_404(
            Post,
            slug=self.kwargs["slug"],
            status=Post.Status.PUBLISHED,
        )

    def get(self, request, slug, *args, **kwargs):
        post = self.get_post()

        queryset = (
            Comment.objects.filter(
                post=post,
                parent__isnull=True,
                is_approved=True,
            )
            .prefetch_related("replies")
            .order_by("-created_at")
        )

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    def post(self, request, slug, *args, **kwargs):
        post = self.get_post()

        serializer = self.get_serializer(
            data=request.data,
            context={
                **self.get_serializer_context(),
                "post": post,
            },
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()

        return Response(
            {
                "message": (
                    "Your comment is awaiting approval."
                ),
                "comment_id": comment.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class CommentModerationViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsOwner]
    serializer_class = CommentModerationSerializer
    pagination_class = CommentPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CommentModerationFilter
    http_method_names = [
        "get",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return (
            Comment.objects
            .select_related("post", "parent")
            .order_by("is_approved", "-created_at")
        )