from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    CategoryViewSet,
    CommentModerationViewSet,
    PostCommentsView,
    PostLikeToggleView,
    PostViewSet,
    TagViewSet,
)

app_name = "blog"


router = SimpleRouter()
router.register(
    "categories",
    CategoryViewSet,
    basename="category",
)
router.register(
    "tags",
    TagViewSet,
    basename="tag",
)
router.register(
    "posts",
    PostViewSet,
    basename="post",
)
router.register(
    "comments",
    CommentModerationViewSet,
    basename="comment",
)


urlpatterns = [
    path(
        "posts/<slug:slug>/like/",
        PostLikeToggleView.as_view(),
        name="post-like",
    ),
    path(
        "posts/<slug:slug>/comments/",
        PostCommentsView.as_view(),
        name="post-comments",
    ),
]

urlpatterns += router.urls