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
            "owner",
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

    def validate(self, attrs):
        """Apply approval rules.

        Publisher articles are approved by that publisher's editors;
        independent articles are approved by their authoring journalist.
        """
        attrs = super().validate(attrs)
        request = self.context.get("request")
        if not (request and attrs.get("approved", False)):
            return attrs
        if self.instance is None or self.instance.approved:
            # New articles always start unapproved (enforced in the view).
            return attrs
        publisher = attrs.get("publisher", self.instance.publisher)
        user = request.user
        if publisher is None:
            allowed = (
                user.role == RoleChoices.JOURNALIST
                and self.instance.author_id == user.id
            )
        else:
            allowed = (
                user.role == RoleChoices.EDITOR
                and publisher.editors.filter(pk=user.pk).exists()
            )
        if not allowed:
            raise serializers.ValidationError({
                "approved": (
                    "Publisher articles are approved by that publisher's "
                    "editors; independent articles by their author."
                )
            })
        return attrs


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

