from django.contrib import admin
from django.db.models import Count, Q

from .models import Category, Comment, Post, PostLike, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "published_posts_count",
        "updated_at",
    )
    search_fields = (
        "name",
        "slug",
        "description",
    )
    list_filter = (
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "slug",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                published_posts_total=Count(
                    "posts",
                    filter=Q(
                        posts__status=Post.Status.PUBLISHED
                    ),
                    distinct=True,
                )
            )
        )

    @admin.display(
        ordering="published_posts_total",
        description="Published posts",
    )
    def published_posts_count(self, obj):
        return obj.published_posts_total


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "published_posts_count",
        "updated_at",
    )
    search_fields = ("name", "slug")
    list_filter = (
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "slug",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                published_posts_total=Count(
                    "posts",
                    filter=Q(
                        posts__status=Post.Status.PUBLISHED
                    ),
                    distinct=True,
                )
            )
        )

    @admin.display(
        ordering="published_posts_total",
        description="Published posts",
    )
    def published_posts_count(self, obj):
        return obj.published_posts_total


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "category",
        "author",
        "published_at",
        "views_count",
        "reading_time",
        "is_featured",
        "updated_at",
    )
    search_fields = (
        "title",
        "excerpt",
        "content",
        "author__username",
        "category__name",
        "tags__name",
    )
    list_filter = (
        "status",
        "category",
        "tags",
        "is_featured",
        "published_at",
        "created_at",
    )
    filter_horizontal = ("tags",)
    list_select_related = (
        "category",
        "author",
    )
    readonly_fields = (
        "slug",
        "published_at",
        "views_count",
        "reading_time",
        "created_at",
        "updated_at",
    )
    ordering = ("-published_at", "-created_at")


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = (
        "post",
        "visitor_id",
        "ip_address",
        "created_at",
    )
    search_fields = (
        "post__title",
        "visitor_id",
        "ip_address",
    )
    list_filter = (
        "created_at",
        "updated_at",
    )
    list_select_related = ("post",)
    readonly_fields = (
        "post",
        "visitor_id",
        "ip_address",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.action(description="Approve selected comments")
def approve_comments(modeladmin, request, queryset):
    queryset.update(is_approved=True)


@admin.action(description="Unapprove selected comments")
def unapprove_comments(modeladmin, request, queryset):
    queryset.update(is_approved=False)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "post",
        "content_preview",
        "parent",
        "is_approved",
        "created_at",
    )
    search_fields = (
        "name",
        "email",
        "content",
        "post__title",
    )
    list_filter = (
        "is_approved",
        "post",
        "created_at",
        "updated_at",
    )
    list_select_related = (
        "post",
        "parent",
    )
    list_editable = ("is_approved",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
    actions = (
        approve_comments,
        unapprove_comments,
    )

    @admin.display(description="Comment")
    def content_preview(self, obj):
        if len(obj.content) <= 60:
            return obj.content

        return f"{obj.content[:60]}..."