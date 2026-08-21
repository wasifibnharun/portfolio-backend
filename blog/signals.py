from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Comment


@receiver(
    post_save,
    sender=Comment,
    dispatch_uid="blog.pending_comment_notification",
)
def notify_owner_about_pending_comment(
    sender,
    instance,
    created,
    **kwargs,
):
    if not created or instance.is_approved:
        return

    User = get_user_model()

    recipients = list(
        User.objects.filter(
            is_superuser=True,
            is_active=True,
        )
        .exclude(email="")
        .values_list("email", flat=True)
    )

    if not recipients:
        recipients = [settings.DEFAULT_FROM_EMAIL]

    send_mail(
        subject="New comment awaiting approval",
        message=(
            f"A new comment was submitted by {instance.name}.\n\n"
            f"Post: {instance.post.title}\n"
            f"Comment: {instance.content}\n\n"
            "Log in to the Django admin or dashboard to review it."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )