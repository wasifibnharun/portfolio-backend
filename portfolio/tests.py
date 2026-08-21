import tempfile
from datetime import date, timedelta
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)

User = get_user_model()


def create_test_image(filename="test.png"):
    buffer = BytesIO()

    Image.new(
        mode="RGB",
        size=(20, 20),
        color="blue",
    ).save(buffer, format="PNG")

    buffer.seek(0)

    return SimpleUploadedFile(
        filename,
        buffer.read(),
        content_type="image/png",
    )


def create_test_pdf(filename="resume.pdf"):
    return SimpleUploadedFile(
        filename,
        b"%PDF-1.4\nTest resume\n%%EOF",
        content_type="application/pdf",
    )


class PortfolioAPITests(APITestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_directory = tempfile.TemporaryDirectory(
            dir=settings.BASE_DIR,
        )
        cls.media_override = override_settings(
            MEDIA_ROOT=cls.media_directory.name
        )
        cls.media_override.enable()

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        cls.media_override.disable()
        cls.media_directory.cleanup()

    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_superuser(
            username="portfolio-owner",
            email="owner@example.com",
            password="OwnerPassword!934",
        )
        self.normal_user = User.objects.create_user(
            username="normal-user",
            email="normal@example.com",
            password="NormalPassword!934",
        )

        self.profile = Profile.objects.create(
            full_name="Test Owner",
            headline="Backend Developer",
            bio="A test owner biography.",
            email="owner@example.com",
            phone="+8801000000000",
            location="Dhaka, Bangladesh",
            avatar=create_test_image(),
            resume=create_test_pdf(),
            github_url="https://github.com/example",
            linkedin_url="https://linkedin.com/in/example",
            years_of_experience=2,
            is_available_for_hire=True,
        )

    def authenticate(self, user):
        access = RefreshToken.for_user(user).access_token

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

    def test_public_profile_returns_absolute_file_urls(self):
        response = self.client.get(
            reverse("portfolio:profile")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            response.data["avatar"].startswith(
                "http://testserver/media/"
            )
        )
        self.assertTrue(
            response.data["resume"].startswith(
                "http://testserver/media/"
            )
        )

    def test_profile_is_singleton(self):
        with self.assertRaises(ValidationError):
            Profile.objects.create(
                full_name="Second Owner",
                headline="Developer",
                bio="Another profile.",
                email="second@example.com",
                phone="+8801000000001",
                location="Dhaka",
                avatar=create_test_image("second.png"),
                resume=create_test_pdf("second.pdf"),
            )

    def test_profile_write_permissions(self):
        anonymous_response = self.client.patch(
            reverse("portfolio:profile"),
            {"headline": "Changed anonymously"},
            format="json",
        )

        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate(self.owner)

        owner_response = self.client.patch(
            reverse("portfolio:profile"),
            {"headline": "Senior Backend Developer"},
            format="json",
        )

        self.assertEqual(
            owner_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            owner_response.data["headline"],
            "Senior Backend Developer",
        )

    def test_skill_filter_search_and_ordering(self):
        Skill.objects.create(
            name="Python",
            category=Skill.Category.BACKEND,
            proficiency=95,
            display_order=2,
            is_featured=True,
        )
        Skill.objects.create(
            name="Django",
            category=Skill.Category.BACKEND,
            proficiency=90,
            display_order=1,
            is_featured=True,
        )
        Skill.objects.create(
            name="Communication",
            category=Skill.Category.SOFT_SKILL,
            proficiency=85,
        )

        response = self.client.get(
            reverse("portfolio:skill-list"),
            {
                "category": Skill.Category.BACKEND,
                "is_featured": "true",
                "search": "python",
                "ordering": "-proficiency",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Python")

    def test_skill_write_permissions(self):
        payload = {
            "name": "PostgreSQL",
            "category": Skill.Category.DATABASE,
            "proficiency": 90,
            "display_order": 1,
            "is_featured": True,
        }

        anonymous_response = self.client.post(
            reverse("portfolio:skill-list"),
            payload,
            format="json",
        )

        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate(self.normal_user)

        normal_response = self.client.post(
            reverse("portfolio:skill-list"),
            payload,
            format="json",
        )

        self.assertEqual(
            normal_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.authenticate(self.owner)

        owner_response = self.client.post(
            reverse("portfolio:skill-list"),
            payload,
            format="json",
        )

        self.assertEqual(
            owner_response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_experience_validation(self):
        self.authenticate(self.owner)

        future_response = self.client.post(
            reverse("portfolio:experience-list"),
            {
                "company": "Example Company",
                "role": "Developer",
                "employment_type": (
                    Experience.EmploymentType.FULL_TIME
                ),
                "location": "Dhaka",
                "start_date": (
                    date.today() + timedelta(days=1)
                ).isoformat(),
                "is_current": True,
                "description": "Future position.",
                "display_order": 0,
            },
            format="json",
        )

        self.assertEqual(
            future_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("start_date", future_response.data)

        missing_end_response = self.client.post(
            reverse("portfolio:experience-list"),
            {
                "company": "Example Company",
                "role": "Developer",
                "employment_type": (
                    Experience.EmploymentType.FULL_TIME
                ),
                "location": "Dhaka",
                "start_date": "2024-01-01",
                "is_current": False,
                "description": "Past position.",
                "display_order": 0,
            },
            format="json",
        )

        self.assertEqual(
            missing_end_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("end_date", missing_end_response.data)

    def test_experiences_are_ordered_by_newest_start_date(self):
        Experience.objects.create(
            company="Older Company",
            role="Junior Developer",
            employment_type=Experience.EmploymentType.FULL_TIME,
            location="Dhaka",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 1, 1),
            is_current=False,
            description="Older experience.",
        )
        Experience.objects.create(
            company="Current Company",
            role="Developer",
            employment_type=Experience.EmploymentType.FULL_TIME,
            location="Dhaka",
            start_date=date(2024, 1, 1),
            end_date=None,
            is_current=True,
            description="Current experience.",
        )

        response = self.client.get(
            reverse("portfolio:experience-list")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data[0]["company"],
            "Current Company",
        )

    def test_education_is_public_and_owner_can_create(self):
        Education.objects.create(
            institution="Example University",
            degree="BSc",
            field_of_study="Computer Science",
            start_year=2020,
            end_year=2024,
        )

        public_response = self.client.get(
            reverse("portfolio:education-list")
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(public_response.data), 1)

        self.authenticate(self.owner)

        create_response = self.client.post(
            reverse("portfolio:education-list"),
            {
                "institution": "Example Institute",
                "degree": "Certificate",
                "field_of_study": "Web Development",
                "start_year": 2024,
                "end_year": 2025,
                "grade": "",
                "description": "Professional course.",
            },
            format="json",
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )

class ProjectAPITests(APITestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_directory = tempfile.TemporaryDirectory(
            dir=settings.BASE_DIR,
        )
        cls.media_override = override_settings(
            MEDIA_ROOT=cls.media_directory.name
        )
        cls.media_override.enable()

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        cls.media_override.disable()
        cls.media_directory.cleanup()

    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_superuser(
            username="project-owner",
            email="project-owner@example.com",
            password="OwnerPassword!934",
        )

        self.python = Skill.objects.create(
            name="Python",
            category=Skill.Category.BACKEND,
            proficiency=95,
        )
        self.postgresql = Skill.objects.create(
            name="PostgreSQL",
            category=Skill.Category.DATABASE,
            proficiency=90,
        )

        self.projects = []

        for index in range(10):
            project = Project.objects.create(
                title=f"Project {index}",
                summary=f"Summary for project {index}.",
                description=(
                    f"Detailed description for project {index}."
                ),
                cover_image=create_test_image(
                    f"project-{index}.png"
                ),
                category=(
                    Project.Category.WEB
                    if index < 5
                    else Project.Category.API
                ),
                live_url=(
                    f"https://example.com/project-{index}"
                ),
                github_url="",
                is_featured=index < 2,
                completed_date=(
                    date(2024, 1, 1)
                    + timedelta(days=index)
                ),
                display_order=0,
            )

            if index % 2 == 0:
                project.tech_stack.add(self.python)
            else:
                project.tech_stack.add(self.postgresql)

            self.projects.append(project)

    def authenticate_owner(self):
        access = RefreshToken.for_user(
            self.owner
        ).access_token

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

    def test_project_list_is_paginated_nine_per_page(self):
        response = self.client.get(
            reverse("portfolio:project-list")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 10)
        self.assertEqual(len(response.data["results"]), 9)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_project_detail_uses_slug_and_absolute_image_url(self):
        project = self.projects[0]

        response = self.client.get(
            reverse(
                "portfolio:project-detail",
                kwargs={"slug": project.slug},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], project.slug)
        self.assertTrue(
            response.data["cover_image"].startswith(
                "http://testserver/media/"
            )
        )
        self.assertEqual(
            response.data["tech_stack"][0]["name"],
            "Python",
        )

        id_response = self.client.get(
            f"/api/projects/{project.pk}/"
        )

        self.assertEqual(
            id_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_project_filters_search_and_ordering(self):
        skill_id_response = self.client.get(
            reverse("portfolio:project-list"),
            {"tech": self.python.pk},
        )

        self.assertEqual(
            skill_id_response.data["count"],
            5,
        )

        skill_name_response = self.client.get(
            reverse("portfolio:project-list"),
            {"tech": "postgresql"},
        )

        self.assertEqual(
            skill_name_response.data["count"],
            5,
        )

        category_response = self.client.get(
            reverse("portfolio:project-list"),
            {
                "category": Project.Category.WEB,
                "is_featured": "true",
            },
        )

        self.assertEqual(
            category_response.data["count"],
            2,
        )

        search_response = self.client.get(
            reverse("portfolio:project-list"),
            {"search": "Project 1"},
        )

        self.assertEqual(search_response.data["count"], 1)

        ordering_response = self.client.get(
            reverse("portfolio:project-list"),
            {"ordering": "completed_date"},
        )

        self.assertEqual(
            ordering_response.data["results"][0]["title"],
            "Project 0",
        )

    def test_project_write_permissions_and_creation(self):
        anonymous_response = self.client.post(
            reverse("portfolio:project-list"),
            {},
            format="json",
        )

        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate_owner()

        create_response = self.client.post(
            reverse("portfolio:project-list"),
            {
                "title": "New Portfolio API",
                "summary": "A new API project.",
                "description": (
                    "A detailed description of the API project."
                ),
                "cover_image": create_test_image(
                    "new-project.png"
                ),
                "tech_stack": [self.python.pk],
                "category": Project.Category.API,
                "live_url": "",
                "github_url": (
                    "https://github.com/example/new-api"
                ),
                "is_featured": True,
                "completed_date": "2025-01-01",
                "display_order": 1,
            },
            format="multipart",
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            create_response.data["tech_stack"][0]["name"],
            "Python",
        )
        self.assertTrue(create_response.data["slug"])

    def test_project_requires_live_or_github_url(self):
        self.authenticate_owner()

        response = self.client.post(
            reverse("portfolio:project-list"),
            {
                "title": "Invalid Project",
                "summary": "Project without a URL.",
                "description": (
                    "This project intentionally has no project URL."
                ),
                "cover_image": create_test_image(
                    "invalid-project.png"
                ),
                "tech_stack": [self.python.pk],
                "category": Project.Category.WEB,
                "live_url": "",
                "github_url": "",
                "is_featured": False,
                "completed_date": "2025-01-01",
                "display_order": 0,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("live_url", response.data)
        self.assertIn("github_url", response.data)