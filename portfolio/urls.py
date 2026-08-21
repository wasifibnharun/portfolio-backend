from django.urls import path
from rest_framework.routers import SimpleRouter

from .dashboard import DashboardStatsView
from .views import (
    ContactMessageViewSet,
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
router.register(
    "contact",
    ContactMessageViewSet,
    basename="contact",
)


urlpatterns = [
    path(
        "profile/",
        ProfileView.as_view(),
        name="profile",
    ),
    path(
        "dashboard/stats/",
        DashboardStatsView.as_view(),
        name="dashboard-stats",
    ),
]

urlpatterns += router.urls