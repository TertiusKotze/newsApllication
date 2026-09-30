"""Signals for role groups and article-approval side effects."""

import requests
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.mail import send_mail
from django.db.models.signals import post_migrate, post_save, pre_save
from django.dispatch import receiver

from .models import Article, RoleChoices, User


def _configure_role_groups():
    """Create Reader, Editor, and Journalist groups with permissions."""
    model_permissions = {
        "article": {
            "view": "view_article",
            "add": "add_article",
            "change": "change_article",
            "delete": "delete_article",
        },
        "newsletter": {
            "view": "view_newsletter",
            "add": "add_newsletter",
            "change": "change_newsletter",
            "delete": "delete_newsletter",
        },
    }

    reader_group, _ = Group.objects.get_or_create(name="Reader")
    editor_group, _ = Group.objects.get_or_create(name="Editor")
    journalist_group, _ = Group.objects.get_or_create(name="Journalist")

    reader_codes = [
        model_permissions["article"]["view"],
        model_permissions["newsletter"]["view"],
    ]
    editor_codes = [
        model_permissions["article"]["view"],
        model_permissions["article"]["change"],
        model_permissions["article"]["delete"],
        model_permissions["newsletter"]["view"],
        model_permissions["newsletter"]["change"],
        model_permissions["newsletter"]["delete"],
    ]
    journalist_codes = [
        model_permissions["article"]["view"],
        model_permissions["article"]["add"],
        model_permissions["article"]["change"],
        model_permissions["article"]["delete"],
        model_permissions["newsletter"]["view"],
        model_permissions["newsletter"]["add"],
        model_permissions["newsletter"]["change"],
        model_permissions["newsletter"]["delete"],
    ]

    reader_group.permissions.set(
        Permission.objects.filter(codename__in=reader_codes)
    )
    editor_group.permissions.set(
        Permission.objects.filter(codename__in=editor_codes)
    )
    journalist_group.permissions.set(
        Permission.objects.filter(codename__in=journalist_codes)
    )


@receiver(post_migrate)
def create_role_groups(sender, **kwargs):
    """Ensure role groups exist after every migration."""
    _configure_role_groups()


@receiver(post_save, sender=User)
def assign_user_group(sender, instance, **kwargs):
    """Keep the user's Django group aligned with their role."""
    instance.assign_group_from_role()


@receiver(pre_save, sender=Article)
def article_pre_save(sender, instance, **kwargs):
    """Remember whether the article was already approved."""
    if not instance.pk:
        instance._was_approved = False
        return
    previous = Article.objects.filter(pk=instance.pk).only(
        "approved"
    ).first()
    instance._was_approved = bool(previous and previous.approved)


@receiver(post_save, sender=Article)
def article_approval_side_effects(sender, instance, created, **kwargs):
    """Email subscribers and log the article to the internal API.

    This runs only on the transition from unapproved to approved so
    later edits do not spam subscribers.
    """
    already_approved = getattr(instance, "_was_approved", False)
    if created or not instance.approved or already_approved:
        return

    recipient_emails = set(
        User.objects.filter(
            role=RoleChoices.READER,
            subscribed_journalists=instance.author,
            email__isnull=False,
        )
        .exclude(email="")
        .values_list("email", flat=True)
    )

    if instance.publisher_id:
        publisher_subscribers = (
            User.objects.filter(
                role=RoleChoices.READER,
                subscribed_publishers=instance.publisher,
                email__isnull=False,
            )
            .exclude(email="")
            .values_list("email", flat=True)
        )
        recipient_emails.update(publisher_subscribers)

    if recipient_emails:
        try:
            send_mail(
                subject=f"Approved article: {instance.title}",
                message=instance.content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=sorted(recipient_emails),
                fail_silently=True,
            )
        except Exception:
            # Email must never block editorial approval.
            pass

    payload = {
        "article_id": instance.id,
        "title": instance.title,
        "author": instance.author.username,
        "publisher": (
            instance.publisher.name if instance.publisher else None
        ),
        "approved_at": instance.created_at.isoformat(),
    }

    try:
        requests.post(
            f"{settings.INTERNAL_API_BASE_URL}/api/approved/",
            json=payload,
            headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
            timeout=2,
        )
    except requests.RequestException:
        # Integration failures must not roll back approval.
        pass
