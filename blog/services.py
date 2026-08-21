import hashlib

from django.conf import settings
from django.core.cache import cache
from django.db.models import F

from .models import Post


def record_post_view(post, request):
    """
    Increment a published post once per visitor/session during
    the configured cooldown. Returns True when incremented.
    """
    user = request.user

    if post.status != Post.Status.PUBLISHED:
        return False

    # Owner previews should not inflate public view statistics.
    if user.is_authenticated and user.is_superuser:
        return False

    visitor_id = request.headers.get(
        "X-Visitor-Id",
        "",
    ).strip()

    if visitor_id:
        identity = f"visitor:{visitor_id}"
    else:
        if not request.session.session_key:
            request.session.create()

        identity = f"session:{request.session.session_key}"

    identity_hash = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()

    cache_key = f"post-view:{post.pk}:{identity_hash}"
    cooldown = settings.POST_VIEW_COOLDOWN_SECONDS

    first_view_during_cooldown = cache.add(
        cache_key,
        True,
        timeout=cooldown,
    )

    if not first_view_during_cooldown:
        return False

    Post.objects.filter(pk=post.pk).update(
        views_count=F("views_count") + 1
    )

    return True