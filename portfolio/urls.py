from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    EducationViewSet,
    ExperienceViewSet,
    ProfileView,
    ProjectViewSet,
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
router.register(
    "projects",
    ProjectViewSet,
    basename="project",
)


urlpatterns = [
    path(
        "profile/",
        ProfileView.as_view(),
        name="profile",
    ),
]

urlpatterns += router.urls