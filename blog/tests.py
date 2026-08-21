import tempfile
from io import BytesIO
from unittest.mock import patch

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

from .models import Category, Comment, Post, PostLike, Tag

User = get_user_model()


def create_blog_image(filename="post.png"):
    buffer = BytesIO()

    Image.new(
        mode="RGB",
        size=(20, 20),
        color="green",
    ).save(buffer, format="PNG")

    buffer.seek(0)

    return SimpleUploadedFile(
        filename,
        buffer.read(),
        content_type="image/png",
    )


class BlogAPITests(APITestCase):
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
            username="blog-owner",
            email="blog-owner@example.com",
            password="OwnerPassword!934",
        )

        self.web_category = Category.objects.create(
            name="Web Development",
            description="Web development posts.",
        )
        self.python_category = Category.objects.create(
            name="Python",
            description="Python posts.",
        )

        self.django_tag = Tag.objects.create(name="Django")
        self.api_tag = Tag.objects.create(name="API")

        self.posts = []

        for index in range(7):
            post = Post.objects.create(
                title=f"Published Post {index}",
                excerpt=f"Excerpt for published post {index}.",
                content=(
                    f"Content for published post {index}. "
                    * 15
                ),
                cover_image=create_blog_image(
                    f"published-{index}.png"
                ),
                category=(
                    self.web_category
                    if index < 4
                    else self.python_category
                ),
                author=self.owner,
                status=Post.Status.PUBLISHED,
                is_featured=index < 2,
            )
            post.tags.add(self.django_tag, self.api_tag)
            self.posts.append(post)

        self.draft = Post.objects.create(
            title="Private Draft Post",
            excerpt="This draft must remain private.",
            content="Draft content.",
            cover_image=create_blog_image("draft.png"),
            category=self.python_category,
            author=self.owner,
            status=Post.Status.DRAFT,
            is_featured=False,
        )
        self.draft.tags.add(self.django_tag)

    def authenticate_owner(self):
        access = RefreshToken.for_user(
            self.owner
        ).access_token

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

    def test_public_list_contains_only_published_posts(self):
        response = self.client.get(
            reverse("blog:post-list")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 7)
        self.assertEqual(len(response.data["results"]), 6)

        returned_slugs = {
            post["slug"]
            for post in response.data["results"]
        }

        self.assertNotIn(self.draft.slug, returned_slugs)

    def test_owner_can_filter_drafts_and_all_posts(self):
        self.authenticate_owner()

        draft_response = self.client.get(
            reverse("blog:post-list"),
            {"status": "DRAFT"},
        )

        self.assertEqual(draft_response.data["count"], 1)
        self.assertEqual(
            draft_response.data["results"][0]["slug"],
            self.draft.slug,
        )

        all_response = self.client.get(
            reverse("blog:post-list"),
            {"status": "all"},
        )

        self.assertEqual(all_response.data["count"], 8)

    def test_draft_detail_is_hidden_from_visitor(self):
        public_response = self.client.get(
            reverse(
                "blog:post-detail",
                kwargs={"slug": self.draft.slug},
            )
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.authenticate_owner()

        owner_response = self.client.get(
            reverse(
                "blog:post-detail",
                kwargs={"slug": self.draft.slug},
            )
        )

        self.assertEqual(
            owner_response.status_code,
            status.HTTP_200_OK,
        )

    def test_post_filters_search_and_likes_ordering(self):
        PostLike.objects.create(
            post=self.posts[3],
            visitor_id="visitor-one",
        )
        PostLike.objects.create(
            post=self.posts[3],
            visitor_id="visitor-two",
        )
        PostLike.objects.create(
            post=self.posts[2],
            visitor_id="visitor-one",
        )

        category_response = self.client.get(
            reverse("blog:post-list"),
            {"category": self.web_category.slug},
        )
        self.assertEqual(category_response.data["count"], 4)

        tag_response = self.client.get(
            reverse("blog:post-list"),
            {"tag": self.django_tag.slug},
        )
        self.assertEqual(tag_response.data["count"], 7)

        featured_response = self.client.get(
            reverse("blog:post-list"),
            {"is_featured": "true"},
        )
        self.assertEqual(featured_response.data["count"], 2)

        search_response = self.client.get(
            reverse("blog:post-list"),
            {"search": "Published Post 1"},
        )
        self.assertEqual(search_response.data["count"], 1)

        ordering_response = self.client.get(
            reverse("blog:post-list"),
            {"ordering": "-likes_count"},
        )
        self.assertEqual(
            ordering_response.data["results"][0]["slug"],
            self.posts[3].slug,
        )

    def test_taxonomy_counts_only_published_posts(self):
        category_response = self.client.get(
            reverse("blog:category-list")
        )

        web_data = next(
            item
            for item in category_response.data
            if item["slug"] == self.web_category.slug
        )
        python_data = next(
            item
            for item in category_response.data
            if item["slug"] == self.python_category.slug
        )

        self.assertEqual(web_data["posts_count"], 4)
        self.assertEqual(python_data["posts_count"], 3)

        tag_response = self.client.get(
            reverse("blog:tag-list")
        )

        django_data = next(
            item
            for item in tag_response.data
            if item["slug"] == self.django_tag.slug
        )

        self.assertEqual(django_data["posts_count"], 7)

    def test_used_category_returns_readable_delete_error(self):
        self.authenticate_owner()

        response = self.client.delete(
            reverse(
                "blog:category-detail",
                kwargs={"pk": self.web_category.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("detail", response.data)
        self.assertTrue(
            Category.objects.filter(
                pk=self.web_category.pk
            ).exists()
        )

    def test_owner_can_create_published_post(self):
        anonymous_response = self.client.post(
            reverse("blog:post-list"),
            {},
            format="json",
        )

        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate_owner()

        response = self.client.post(
            reverse("blog:post-list"),
            {
                "title": "New Django REST Article",
                "excerpt": "An article created through the API.",
                "content": (
                    "This is substantial original article content. "
                    * 10
                ),
                "cover_image": create_blog_image("new-post.png"),
                "category": self.web_category.pk,
                "tags": [
                    self.django_tag.pk,
                    self.api_tag.pk,
                ],
                "status": Post.Status.PUBLISHED,
                "is_featured": True,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["author"]["username"],
            self.owner.username,
        )
        self.assertIsNotNone(response.data["published_at"])
        self.assertGreater(response.data["reading_time"], 0)

    def test_detail_counts_like_state_and_related_posts(self):
        selected_post = self.posts[0]

        PostLike.objects.create(
            post=selected_post,
            visitor_id="visitor-one",
        )
        PostLike.objects.create(
            post=selected_post,
            visitor_id="visitor-two",
        )

        Comment.objects.bulk_create(
            [
                Comment(
                    post=selected_post,
                    name="Approved One",
                    email="one@example.com",
                    content="First approved comment.",
                    is_approved=True,
                ),
                Comment(
                    post=selected_post,
                    name="Approved Two",
                    email="two@example.com",
                    content="Second approved comment.",
                    is_approved=True,
                ),
                Comment(
                    post=selected_post,
                    name="Pending User",
                    email="pending@example.com",
                    content="Pending comment.",
                    is_approved=False,
                ),
            ]
        )

        response = self.client.get(
            reverse(
                "blog:post-detail",
                kwargs={"slug": selected_post.slug},
            ),
            HTTP_X_VISITOR_ID="visitor-one",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["likes_count"], 2)
        self.assertEqual(response.data["comments_count"], 2)
        self.assertTrue(response.data["is_liked"])
        self.assertLessEqual(
            len(response.data["related_posts"]),
            3,
        )
        self.assertTrue(
            response.data["cover_image"].startswith(
                "http://testserver/media/"
            )
        )

class BlogInteractionAPITests(APITestCase):
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
            username="interaction-owner",
            email="owner@example.com",
            password="OwnerPassword!934",
        )
        self.normal_user = User.objects.create_user(
            username="interaction-user",
            email="user@example.com",
            password="NormalPassword!934",
        )

        self.category = Category.objects.create(
            name="Interaction Category"
        )
        self.tag = Tag.objects.create(
            name="Interaction Tag"
        )

        self.post = Post.objects.create(
            title="Published Interaction Post",
            excerpt="Testing blog interactions.",
            content="Published interaction content. " * 15,
            cover_image=create_blog_image("interaction.png"),
            category=self.category,
            author=self.owner,
            status=Post.Status.PUBLISHED,
        )
        self.post.tags.add(self.tag)

        self.related_post = Post.objects.create(
            title="Related Interaction Post",
            excerpt="Related post.",
            content="Related published content. " * 15,
            cover_image=create_blog_image("related.png"),
            category=self.category,
            author=self.owner,
            status=Post.Status.PUBLISHED,
        )
        self.related_post.tags.add(self.tag)

        self.draft = Post.objects.create(
            title="Draft Interaction Post",
            excerpt="Private draft.",
            content="Private draft content.",
            cover_image=create_blog_image("interaction-draft.png"),
            category=self.category,
            author=self.owner,
            status=Post.Status.DRAFT,
        )
        self.draft.tags.add(self.tag)

    def authenticate(self, user):
        access = RefreshToken.for_user(user).access_token

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

    def test_like_requires_visitor_header(self):
        response = self.client.post(
            reverse(
                "blog:post-like",
                kwargs={"slug": self.post.slug},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_like_is_an_idempotent_toggle(self):
        url = reverse(
            "blog:post-like",
            kwargs={"slug": self.post.slug},
        )

        first = self.client.post(
            url,
            HTTP_X_VISITOR_ID="visitor-abc",
        )
        second = self.client.post(
            url,
            HTTP_X_VISITOR_ID="visitor-abc",
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertTrue(first.data["liked"])
        self.assertEqual(first.data["likes_count"], 1)

        self.assertFalse(second.data["liked"])
        self.assertEqual(second.data["likes_count"], 0)

    def test_draft_cannot_be_liked_publicly(self):
        response = self.client.post(
            reverse(
                "blog:post-like",
                kwargs={"slug": self.draft.slug},
            ),
            HTTP_X_VISITOR_ID="visitor-abc",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_view_counter_uses_visitor_cooldown(self):
        url = reverse(
            "blog:post-detail",
            kwargs={"slug": self.post.slug},
        )

        self.client.get(
            url,
            HTTP_X_VISITOR_ID="visitor-one",
        )
        self.client.get(
            url,
            HTTP_X_VISITOR_ID="visitor-one",
        )

        self.post.refresh_from_db()
        self.assertEqual(self.post.views_count, 1)

        response = self.client.get(
            url,
            HTTP_X_VISITOR_ID="visitor-two",
        )

        self.post.refresh_from_db()
        self.assertEqual(self.post.views_count, 2)
        self.assertEqual(response.data["views_count"], 2)

    def test_view_counter_falls_back_to_session(self):
        url = reverse(
            "blog:post-detail",
            kwargs={"slug": self.post.slug},
        )

        self.client.get(url)
        self.client.get(url)

        self.post.refresh_from_db()
        self.assertEqual(self.post.views_count, 1)

    def test_public_comments_are_approved_threaded_and_private(self):
        parent = Comment.objects.create(
            post=self.post,
            name="Parent User",
            email="private@example.com",
            content="Approved parent comment.",
            is_approved=True,
        )
        Comment.objects.create(
            post=self.post,
            name="Reply User",
            email="reply@example.com",
            content="Approved reply comment.",
            parent=parent,
            is_approved=True,
        )
        Comment.objects.bulk_create(
            [
                Comment(
                    post=self.post,
                    name="Pending User",
                    email="pending@example.com",
                    content="Pending hidden comment.",
                    is_approved=False,
                )
            ]
        )

        response = self.client.get(
            reverse(
                "blog:post-comments",
                kwargs={"slug": self.post.slug},
            )
        )

        self.assertEqual(response.data["count"], 1)
        comment = response.data["results"][0]

        self.assertNotIn("email", comment)
        self.assertEqual(len(comment["replies"]), 1)
        self.assertNotIn("email", comment["replies"][0])

    @patch("blog.signals.send_mail")
    def test_comment_creation_is_pending_and_sends_signal(
        self,
        mocked_send_mail,
    ):
        response = self.client.post(
            reverse(
                "blog:post-comments",
                kwargs={"slug": self.post.slug},
            ),
            {
                "name": "New Visitor",
                "email": "visitor@example.com",
                "website": "",
                "content": "A valid pending comment.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["message"],
            "Your comment is awaiting approval.",
        )

        comment = Comment.objects.get(
            pk=response.data["comment_id"]
        )
        self.assertFalse(comment.is_approved)
        mocked_send_mail.assert_called_once()

    def test_only_one_reply_level_is_allowed(self):
        parent = Comment.objects.create(
            post=self.post,
            name="Parent",
            email="parent@example.com",
            content="Approved parent.",
            is_approved=True,
        )
        reply = Comment.objects.create(
            post=self.post,
            name="Reply",
            email="reply@example.com",
            content="Approved reply.",
            parent=parent,
            is_approved=True,
        )

        response = self.client.post(
            reverse(
                "blog:post-comments",
                kwargs={"slug": self.post.slug},
            ),
            {
                "name": "Nested Reply",
                "email": "nested@example.com",
                "content": "This reply is too deeply nested.",
                "parent": reply.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("parent", response.data)

    def test_comment_moderation_is_owner_only(self):
        pending = Comment.objects.create(
            post=self.post,
            name="Pending",
            email="pending@example.com",
            content="Pending moderation comment.",
            is_approved=False,
        )

        list_url = reverse("blog:comment-list")

        anonymous_response = self.client.get(list_url)
        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate(self.normal_user)
        normal_response = self.client.get(list_url)
        self.assertEqual(
            normal_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.authenticate(self.owner)
        owner_response = self.client.get(
            list_url,
            {
                "is_approved": "false",
                "post": self.post.slug,
            },
        )

        self.assertEqual(owner_response.data["count"], 1)

        approve_response = self.client.patch(
            reverse(
                "blog:comment-detail",
                kwargs={"pk": pending.pk},
            ),
            {"is_approved": True},
            format="json",
        )

        self.assertEqual(
            approve_response.status_code,
            status.HTTP_200_OK,
        )

        pending.refresh_from_db()
        self.assertTrue(pending.is_approved)

    @patch("blog.signals.send_mail")
    def test_comment_creation_throttle(self, mocked_send_mail):
        url = reverse(
            "blog:post-comments",
            kwargs={"slug": self.post.slug},
        )

        for index in range(5):
            response = self.client.post(
                url,
                {
                    "name": f"Visitor {index}",
                    "email": f"visitor{index}@example.com",
                    "content": f"Valid comment number {index}.",
                },
                format="json",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
            )

        throttled = self.client.post(
            url,
            {
                "name": "Sixth Visitor",
                "email": "sixth@example.com",
                "content": "This request should be throttled.",
            },
            format="json",
        )

        self.assertEqual(
            throttled.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )