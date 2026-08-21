import tempfile
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from blog.models import Category, Comment, Post, PostLike, Tag

from .models import ContactMessage, Project, Skill

User = get_user_model()


def create_dashboard_image(filename):
    buffer = BytesIO()

    Image.new(
        mode="RGB",
        size=(20, 20),
        color="purple",
    ).save(buffer, format="PNG")

    buffer.seek(0)

    return SimpleUploadedFile(
        filename,
        buffer.read(),
        content_type="image/png",
    )


class ContactMessageAPITests(APITestCase):
    def setUp(self):
        cache.clear()

        self.owner = User.objects.create_superuser(
            username="contact-owner",
            email="owner@example.com",
            password="OwnerPassword!934",
        )
        self.normal_user = User.objects.create_user(
            username="contact-user",
            email="user@example.com",
            password="NormalPassword!934",
        )

        for index in range(12):
            ContactMessage.objects.create(
                name=f"Visitor {index}",
                email=f"visitor{index}@example.com",
                subject=f"Subject {index}",
                message=f"A valid contact message number {index}.",
                is_read=index % 2 == 0,
            )

    def authenticate(self, user):
        access = RefreshToken.for_user(user).access_token

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

    def test_public_can_create_but_message_is_validated(self):
        valid_response = self.client.post(
            reverse("portfolio:contact-list"),
            {
                "name": "New Visitor",
                "email": "new@example.com",
                "subject": "Project enquiry",
                "message": "I would like to discuss a project.",
            },
            format="json",
        )

        self.assertEqual(
            valid_response.status_code,
            status.HTTP_201_CREATED,
        )

        created = ContactMessage.objects.get(
            pk=valid_response.data["id"]
        )
        self.assertFalse(created.is_read)

        invalid_response = self.client.post(
            reverse("portfolio:contact-list"),
            {
                "name": "A",
                "email": "invalid-email",
                "subject": "",
                "message": "short",
            },
            format="json",
        )

        self.assertEqual(
            invalid_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("message", invalid_response.data)

    def test_contact_creation_is_throttled_three_per_hour(self):
        url = reverse("portfolio:contact-list")

        for index in range(3):
            response = self.client.post(
                url,
                {
                    "name": f"Throttle Visitor {index}",
                    "email": f"throttle{index}@example.com",
                    "subject": f"Throttle subject {index}",
                    "message": (
                        f"Valid throttled message number {index}."
                    ),
                },
                format="json",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
            )

        fourth_response = self.client.post(
            url,
            {
                "name": "Fourth Visitor",
                "email": "fourth@example.com",
                "subject": "Fourth subject",
                "message": "This fourth request must be throttled.",
            },
            format="json",
        )

        self.assertEqual(
            fourth_response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def test_inbox_is_owner_only_filterable_and_paginated(self):
        url = reverse("portfolio:contact-list")

        anonymous_response = self.client.get(url)
        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate(self.normal_user)
        normal_response = self.client.get(url)
        self.assertEqual(
            normal_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.authenticate(self.owner)

        owner_response = self.client.get(url)

        self.assertEqual(owner_response.data["count"], 12)
        self.assertEqual(
            len(owner_response.data["results"]),
            10,
        )

        unread_response = self.client.get(
            url,
            {"is_read": "false"},
        )

        self.assertEqual(unread_response.data["count"], 6)

        unread_message = ContactMessage.objects.filter(
            is_read=False
        ).first()

        patch_response = self.client.patch(
            reverse(
                "portfolio:contact-detail",
                kwargs={"pk": unread_message.pk},
            ),
            {"is_read": True},
            format="json",
        )

        self.assertEqual(
            patch_response.status_code,
            status.HTTP_200_OK,
        )

        unread_message.refresh_from_db()
        self.assertTrue(unread_message.is_read)

        delete_response = self.client.delete(
            reverse(
                "portfolio:contact-detail",
                kwargs={"pk": unread_message.pk},
            )
        )

        self.assertEqual(
            delete_response.status_code,
            status.HTTP_204_NO_CONTENT,
        )


class DashboardStatsAPITests(APITestCase):
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
            username="dashboard-owner",
            email="dashboard@example.com",
            password="OwnerPassword!934",
        )
        self.normal_user = User.objects.create_user(
            username="dashboard-user",
            password="NormalPassword!934",
        )

        self.skill = Skill.objects.create(
            name="Dashboard Python",
            category=Skill.Category.BACKEND,
            proficiency=95,
        )
        self.category = Category.objects.create(
            name="Dashboard Category"
        )
        self.tag = Tag.objects.create(
            name="Dashboard Tag"
        )

        self.posts = []

        for index in range(6):
            post = Post.objects.create(
                title=f"Dashboard Post {index}",
                excerpt=f"Dashboard excerpt {index}.",
                content=(
                    "Substantial dashboard post content. " * 10
                    if index < 4
                    else "Draft dashboard content."
                ),
                cover_image=create_dashboard_image(
                    f"dashboard-post-{index}.png"
                ),
                category=self.category,
                author=self.owner,
                status=(
                    Post.Status.PUBLISHED
                    if index < 4
                    else Post.Status.DRAFT
                ),
                views_count=index * 10,
            )
            post.tags.add(self.tag)
            self.posts.append(post)

        PostLike.objects.create(
            post=self.posts[5],
            visitor_id="dashboard-one",
        )
        PostLike.objects.create(
            post=self.posts[5],
            visitor_id="dashboard-two",
        )
        PostLike.objects.create(
            post=self.posts[4],
            visitor_id="dashboard-one",
        )

        Comment.objects.bulk_create(
            [
                Comment(
                    post=self.posts[index % 6],
                    name=f"Commenter {index}",
                    email=f"commenter{index}@example.com",
                    content=f"Dashboard comment {index}.",
                    is_approved=index < 4,
                )
                for index in range(6)
            ]
        )

        for index in range(2):
            project = Project.objects.create(
                title=f"Dashboard Project {index}",
                summary=f"Project summary {index}.",
                description=f"Project description {index}.",
                cover_image=create_dashboard_image(
                    f"dashboard-project-{index}.png"
                ),
                category=Project.Category.WEB,
                live_url=f"https://example.com/{index}",
                completed_date="2025-01-01",
            )
            project.tech_stack.add(self.skill)

        for index in range(3):
            ContactMessage.objects.create(
                name=f"Dashboard Visitor {index}",
                email=f"dashboard{index}@example.com",
                subject=f"Dashboard subject {index}",
                message=f"Dashboard message number {index}.",
                is_read=index == 0,
            )

    def authenticate(self, user):
        access = RefreshToken.for_user(user).access_token

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

    def test_dashboard_is_owner_only(self):
        url = reverse("portfolio:dashboard-stats")

        anonymous_response = self.client.get(url)
        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate(self.normal_user)
        normal_response = self.client.get(url)
        self.assertEqual(
            normal_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.authenticate(self.owner)
        owner_response = self.client.get(url)
        self.assertEqual(
            owner_response.status_code,
            status.HTTP_200_OK,
        )

    def test_dashboard_returns_all_required_aggregates(self):
        self.authenticate(self.owner)

        response = self.client.get(
            reverse("portfolio:dashboard-stats")
        )

        self.assertEqual(response.data["total_posts"], 6)
        self.assertEqual(response.data["published_posts"], 4)
        self.assertEqual(response.data["draft_posts"], 2)
        self.assertEqual(response.data["total_projects"], 2)
        self.assertEqual(response.data["total_skills"], 1)
        self.assertEqual(response.data["total_comments"], 6)
        self.assertEqual(response.data["pending_comments"], 2)
        self.assertEqual(response.data["total_likes"], 3)
        self.assertEqual(response.data["total_views"], 150)
        self.assertEqual(response.data["unread_messages"], 2)

        self.assertEqual(len(response.data["top_posts"]), 5)
        self.assertEqual(
            response.data["top_posts"][0]["title"],
            "Dashboard Post 5",
        )
        self.assertEqual(
            response.data["top_posts"][0]["views"],
            50,
        )
        self.assertEqual(
            response.data["top_posts"][0]["likes"],
            2,
        )

        self.assertEqual(
            len(response.data["recent_comments"]),
            5,
        )
        self.assertEqual(
            len(response.data["posts_per_month"]),
            6,
        )
        self.assertEqual(
            response.data["posts_per_month"][-1]["count"],
            6,
        )