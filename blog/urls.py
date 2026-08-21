from rest_framework.routers import SimpleRouter

from .views import (
    CategoryViewSet,
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


urlpatterns = router.urls