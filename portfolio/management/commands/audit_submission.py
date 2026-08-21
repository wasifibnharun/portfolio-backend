import re

from django.core.management.base import BaseCommand, CommandError

from blog.models import Category, Comment, Post, Tag
from portfolio.models import (
    ContactMessage,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)


def word_count(value):
    return len(re.findall(r"\b[\w'-]+\b", value or ""))


def stored_file_exists(field_file):
    if not field_file or not field_file.name:
        return False

    try:
        return field_file.storage.exists(field_file.name)
    except OSError:
        return False


class Command(BaseCommand):
    help = "Audit the database against the assignment content requirements."

    def handle(self, *args, **options):
        results = []

        def check(label, passed, details):
            results.append(passed)
            message = f"{label}: {details}"

            if passed:
                self.stdout.write(
                    self.style.SUCCESS(f"[PASS] {message}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"[FAIL] {message}")
                )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\nDevFolio assignment content audit\n"
            )
        )

        # Profile
        profile_count = Profile.objects.count()
        check(
            "Singleton profile",
            profile_count == 1,
            f"found {profile_count}; required exactly 1",
        )

        profile = Profile.objects.first()

        if profile:
            required_profile_values = [
                profile.full_name,
                profile.headline,
                profile.bio,
                profile.email,
                profile.phone,
                profile.location,
            ]

            check(
                "Profile details",
                all(
                    str(value).strip()
                    for value in required_profile_values
                ),
                "name, headline, bio, email, phone, and location",
            )

            check(
                "Profile avatar",
                stored_file_exists(profile.avatar),
                "a stored profile image is required",
            )

            check(
                "Profile resume",
                stored_file_exists(profile.resume),
                "a stored PDF resume is required",
            )

            social_urls = [
                profile.github_url,
                profile.linkedin_url,
                profile.x_url,
                profile.website_url,
            ]
            social_count = sum(
                bool(url.strip())
                for url in social_urls
                if url
            )

            check(
                "Profile social links",
                social_count >= 2,
                f"found {social_count}; required at least 2",
            )

            bio_lines = [
                line.strip()
                for line in profile.bio.splitlines()
                if line.strip()
            ]

            check(
                "Profile bio length",
                4 <= len(bio_lines) <= 8,
                (
                    f"found {len(bio_lines)} non-empty lines; "
                    "required 4-8"
                ),
            )

        # Skills
        skill_count = Skill.objects.count()
        skill_category_count = (
            Skill.objects
            .values("category")
            .distinct()
            .count()
        )

        check(
            "Skills",
            skill_count >= 10,
            f"found {skill_count}; required at least 10",
        )
        check(
            "Skill categories",
            skill_category_count >= 3,
            (
                f"found {skill_category_count}; "
                "required at least 3"
            ),
        )

        # Experience and education
        experience_count = Experience.objects.count()
        education_count = Education.objects.count()
        history_count = experience_count + education_count

        check(
            "Experience and education",
            history_count >= 2,
            (
                f"experience={experience_count}, "
                f"education={education_count}; "
                "required at least 2 combined"
            ),
        )

        # Projects
        projects = Project.objects.prefetch_related("tech_stack")
        project_count = projects.count()

        check(
            "Projects",
            project_count >= 3,
            f"found {project_count}; required at least 3",
        )

        incomplete_projects = []

        for project in projects:
            missing = []

            if not stored_file_exists(project.cover_image):
                missing.append("cover image")

            if project.tech_stack.count() == 0:
                missing.append("technology stack")

            if not project.live_url and not project.github_url:
                missing.append("live/GitHub URL")

            if missing:
                incomplete_projects.append(
                    f"{project.slug}: {', '.join(missing)}"
                )

        check(
            "Project completeness",
            project_count >= 3 and not incomplete_projects,
            (
                "all projects are complete"
                if not incomplete_projects
                else "; ".join(incomplete_projects)
            ),
        )

        # Blog taxonomy
        category_count = Category.objects.count()
        tag_count = Tag.objects.count()

        check(
            "Blog categories",
            category_count >= 3,
            f"found {category_count}; required at least 3",
        )
        check(
            "Blog tags",
            tag_count >= 6,
            f"found {tag_count}; required at least 6",
        )

        # Posts
        posts = Post.objects.all()
        published_posts = posts.filter(
            status=Post.Status.PUBLISHED
        ).prefetch_related("tags")
        draft_count = posts.filter(
            status=Post.Status.DRAFT
        ).count()

        check(
            "Total blog posts",
            posts.count() >= 5,
            f"found {posts.count()}; required at least 5",
        )
        check(
            "Published posts",
            published_posts.count() >= 4,
            (
                f"found {published_posts.count()}; "
                "required at least 4"
            ),
        )
        check(
            "Draft posts",
            draft_count >= 1,
            f"found {draft_count}; required at least 1",
        )

        incomplete_posts = []

        for post in published_posts:
            missing = []
            post_words = word_count(post.content)

            if post_words < 300:
                missing.append(f"only {post_words} words")

            if not stored_file_exists(post.cover_image):
                missing.append("cover image")

            if not post.category_id:
                missing.append("category")

            post_tag_count = post.tags.count()

            if post_tag_count < 2:
                missing.append(
                    f"only {post_tag_count} tag(s)"
                )

            if not post.published_at:
                missing.append("publication timestamp")

            if missing:
                incomplete_posts.append(
                    f"{post.slug}: {', '.join(missing)}"
                )

        check(
            "Published-post completeness",
            published_posts.count() >= 4 and not incomplete_posts,
            (
                "every published post has 300+ words, an image, "
                "a category, and at least 2 tags"
                if not incomplete_posts
                else "; ".join(incomplete_posts)
            ),
        )

        # Comments
        comment_count = Comment.objects.count()
        pending_comment_count = Comment.objects.filter(
            is_approved=False
        ).count()
        reply_count = Comment.objects.filter(
            parent__isnull=False
        ).count()

        check(
            "Comments",
            comment_count >= 5,
            f"found {comment_count}; required at least 5",
        )
        check(
            "Pending comments",
            pending_comment_count >= 2,
            (
                f"found {pending_comment_count}; "
                "required at least 2"
            ),
        )
        check(
            "Comment replies",
            reply_count >= 1,
            f"found {reply_count}; required at least 1",
        )

        # Contact messages
        contact_count = ContactMessage.objects.count()
        unread_contact_count = ContactMessage.objects.filter(
            is_read=False
        ).count()

        check(
            "Contact messages",
            contact_count >= 2,
            f"found {contact_count}; required at least 2",
        )
        check(
            "Unread contact messages",
            unread_contact_count >= 1,
            (
                f"found {unread_contact_count}; "
                "required at least 1"
            ),
        )

        failed_count = results.count(False)

        if failed_count:
            raise CommandError(
                f"\nSubmission audit failed: "
                f"{failed_count} requirement(s) are incomplete."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nSubmission content audit passed completely."
            )
        )