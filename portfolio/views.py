from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    filters,
    generics,
    mixins,
    status,
    viewsets,
)
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from accounts.permissions import IsOwner
from config.throttles import IPScopedRateThrottle

from .filters import ProjectFilter
from .models import (
    ContactMessage,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)
from .pagination import (
    ContactMessagePagination,
    ProjectPagination,
)
from .serializers import (
    ContactMessageCreateSerializer,
    ContactMessageOwnerSerializer,
    EducationSerializer,
    ExperienceSerializer,
    ProfileSerializer,
    ProjectSerializer,
    SkillSerializer,
)


class ProfileView(generics.GenericAPIView):
    serializer_class = ProfileSerializer
    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]
    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]

    def get_object(self):
        profile = Profile.get_solo()

        if profile is None:
            raise NotFound(
                "The owner profile has not been configured yet."
            )

        self.check_object_permissions(self.request, profile)
        return profile

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        profile = self.get_object()

        serializer = self.get_serializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "category",
        "is_featured",
    ]
    search_fields = [
        "name",
    ]
    ordering_fields = [
        "display_order",
        "proficiency",
    ]
    ordering = [
        "display_order",
        "name",
    ]
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]


class ExperienceViewSet(viewsets.ModelViewSet):
    queryset = Experience.objects.all().order_by(
        "-start_date",
        "display_order",
    )
    serializer_class = ExperienceSerializer
    filter_backends = []
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]

class EducationViewSet(viewsets.ModelViewSet):
    queryset = Education.objects.all()
    serializer_class = EducationSerializer
    filter_backends = []
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.prefetch_related(
        "tech_stack"
    )
    serializer_class = ProjectSerializer
    pagination_class = ProjectPagination
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
    filterset_class = ProjectFilter
    search_fields = [
        "title",
        "summary",
        "description",
    ]
    ordering_fields = [
        "completed_date",
        "display_order",
    ]
    ordering = [
        "display_order",
        "-completed_date",
    ]
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]

class ContactMessageViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ContactMessage.objects.all().order_by(
        "-created_at"
    )
    permission_classes = [IsOwner]
    pagination_class = ContactMessagePagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_read"]
    throttle_classes = [
        AnonRateThrottle,
        IPScopedRateThrottle,
    ]
    parser_classes = [
        JSONParser,
        FormParser,
    ]
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]

        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return ContactMessageCreateSerializer

        return ContactMessageOwnerSerializer

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "contact"
        else:
            self.throttle_scope = None

        return super().get_throttles()