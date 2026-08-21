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