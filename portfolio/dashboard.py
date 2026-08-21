from django.db.models import (
    BigIntegerField,
    Count,
    F,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOwner
from blog.models import Comment, Post, PostLike

from .models import ContactMessage, Project, Skill


def shift_month(month, offset):
    month_index = (
        month.year * 12
        + month.month
        - 1
        + offset
    )

    return month.replace(
        year=month_index // 12,
        month=(month_index % 12) + 1,
        day=1,
    )


class DashboardStatsView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        post_stats = Post.objects.aggregate(
            total_posts=Count("id"),
            published_posts=Count(
                "id",
                filter=Q(status=Post.Status.PUBLISHED),
            ),
            draft_posts=Count(
                "id",
                filter=Q(status=Post.Status.DRAFT),
            ),
            total_views=Coalesce(
                Sum("views_count"),
                Value(0),
                output_field=BigIntegerField(),
            ),
        )

        project_stats = Project.objects.aggregate(
            total_projects=Count("id"),
        )
        skill_stats = Skill.objects.aggregate(
            total_skills=Count("id"),
        )
        comment_stats = Comment.objects.aggregate(
            total_comments=Count("id"),
            pending_comments=Count(
                "id",
                filter=Q(is_approved=False),
            ),
        )
        like_stats = PostLike.objects.aggregate(
            total_likes=Count("id"),
        )
        message_stats = ContactMessage.objects.aggregate(
            unread_messages=Count(
                "id",
                filter=Q(is_read=False),
            ),
        )

        top_post_rows = (
            Post.objects
            .annotate(
                likes_total=Count(
                    "likes",
                    distinct=True,
                )
            )
            .values(
                "title",
                "slug",
                "views_count",
                "likes_total",
            )
            .order_by(
                "-views_count",
                "-likes_total",
            )[:5]
        )

        top_posts = [
            {
                "title": row["title"],
                "slug": row["slug"],
                "views": row["views_count"],
                "likes": row["likes_total"],
            }
            for row in top_post_rows
        ]

        recent_comment_rows = (
            Comment.objects
            .annotate(
                post_title=F("post__title"),
                post_slug=F("post__slug"),
            )
            .values(
                "id",
                "post_title",
                "post_slug",
                "name",
                "content",
                "is_approved",
                "created_at",
            )
            .order_by("-created_at")[:5]
        )

        recent_comments = list(recent_comment_rows)

        current_month = timezone.localdate().replace(day=1)
        first_month = shift_month(current_month, -5)

        monthly_rows = (
            Post.objects
            .filter(created_at__date__gte=first_month)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        month_counts = {
            row["month"].date().replace(day=1): row["count"]
            for row in monthly_rows
        }

        posts_per_month = []

        for offset in range(-5, 1):
            month = shift_month(current_month, offset)

            posts_per_month.append(
                {
                    "month": month.strftime("%Y-%m"),
                    "count": month_counts.get(month, 0),
                }
            )

        return Response(
            {
                **post_stats,
                **project_stats,
                **skill_stats,
                **comment_stats,
                **like_stats,
                **message_stats,
                "top_posts": top_posts,
                "recent_comments": recent_comments,
                "posts_per_month": posts_per_month,
            }
        )