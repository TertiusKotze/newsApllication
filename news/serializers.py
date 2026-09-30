"""DRF serializers for users, publishers, articles, and newsletters."""

from rest_framework import serializers

from .models import (
    ApprovedArticleLog,
    Article,
    Newsletter,
    Publisher,
    RoleChoices,
    User,
)


class UserSerializer(serializers.ModelSerializer):
    """Public representation of an application user."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]


class PublisherSerializer(serializers.ModelSerializer):
    """Serializer for curated publications and their staff."""

    class Meta:
        model = Publisher
        fields = [
            "id",
            "name",
            "description",
            "editors",
            "journalists",
        ]


class ArticleSerializer(serializers.ModelSerializer):
    """Serialize articles and prevent non-editors from approving."""

    author = UserSerializer(read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "content",
            "author",
            "created_at",
            "approved",
            "publisher",
        ]
        read_only_fields = ["created_at", "author"]

    def validate_approved(self, value):
        """Only editors may set the approved flag to True."""
        request = self.context.get("request")
        if request and value and request.user.role != RoleChoices.EDITOR:
            raise serializers.ValidationError(
                "Only editors can approve articles."
            )
        return value


class NewsletterSerializer(serializers.ModelSerializer):
    """Serialize newsletters and their linked articles."""

    author = UserSerializer(read_only=True)

    class Meta:
        model = Newsletter
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "author",
            "articles",
        ]
        read_only_fields = ["created_at", "author"]


class ApprovedArticleLogSerializer(serializers.ModelSerializer):
    """Serializer for internally logged approval payloads."""

    class Meta:
        model = ApprovedArticleLog
        fields = ["id", "article", "payload", "received_at"]
        read_only_fields = ["id", "received_at"]

