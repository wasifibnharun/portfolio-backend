from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    EducationViewSet,
    ExperienceViewSet,
    ProfileView,
    SkillViewSet,
)

app_name = "portfolio"


router = SimpleRouter()
router.register(
    "skills",
    SkillViewSet,
    basename="skill",
)
router.register(
    "experiences",
    ExperienceViewSet,
    basename="experience",
)
router.register(
    "education",
    EducationViewSet,
    basename="education",
)


urlpatterns = [
    path(
        "profile/",
        ProfileView.as_view(),
        name="profile",
    ),
]

urlpatterns += router.urls