"""Application configuration for the news app."""

from django.apps import AppConfig


class NewsConfig(AppConfig):
    """Load news models and connect approval/group signals."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'news'

    def ready(self):
        """Import signal handlers when Django starts."""
        from . import signals  # noqa: F401

