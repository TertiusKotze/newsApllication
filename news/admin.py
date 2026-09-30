"""Django admin configuration for news models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ApprovedArticleLog, Article, Newsletter, Publisher, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Manage custom users, including role and reader subscriptions."""

    fieldsets = UserAdmin.fieldsets + (
        (
            "Role and subscriptions",
            {
                "fields": (
                    "role",
                    "subscribed_publishers",
                    "subscribed_journalists",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role", "email")}),
    )
    list_display = ("username", "email", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser")
    filter_horizontal = (
        "subscribed_publishers",
        "subscribed_journalists",
        "groups",
        "user_permissions",
    )


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    """Admin for curated publications and their staff lists."""

    list_display = ("name",)
    search_fields = ("name",)
    filter_horizontal = ("editors", "journalists")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Admin for article moderation and lookup."""

    list_display = (
        "title",
        "author",
        "publisher",
        "approved",
        "created_at",
    )
    list_filter = ("approved", "publisher")
    search_fields = ("title", "content")


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    """Admin for newsletter collections."""

    list_display = ("title", "author", "created_at")
    search_fields = ("title", "description")
    filter_horizontal = ("articles",)


@admin.register(ApprovedArticleLog)
class ApprovedArticleLogAdmin(admin.ModelAdmin):
    """Read-only log of internally posted approval payloads."""

    list_display = ("id", "article", "received_at")
    readonly_fields = ("article", "payload", "received_at")
