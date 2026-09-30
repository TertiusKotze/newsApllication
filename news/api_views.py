"""REST API views for articles, newsletters, and the approval log."""

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ApprovedArticleLog, Article, Newsletter, RoleChoices
from .permissions import (
    IsJournalist,
    IsReader,
    ReadOnlyOrEditorJournalist,
)
from .serializers import ArticleSerializer, NewsletterSerializer


class ArticleListCreateAPIView(generics.ListCreateAPIView):
    """List approved articles or create a journalist submission."""

    serializer_class = ArticleSerializer

    def get_queryset(self):
        """Return approved articles with related author and publisher."""
        return Article.objects.filter(approved=True).select_related(
            'author',
            'publisher',
        )

    def get_permissions(self):
        """Journalists may POST; any authenticated user may GET."""
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsJournalist()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Attach the journalist and keep new articles unapproved."""
        serializer.save(author=self.request.user, approved=False)


class ArticleSubscribedAPIView(generics.ListAPIView):
    """Return approved articles matching a reader's subscriptions."""

    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated, IsReader]

    def get_queryset(self):
        """Filter by subscribed publishers or journalists."""
        user = self.request.user
        return (
            Article.objects.filter(approved=True)
            .filter(
                Q(publisher__in=user.subscribed_publishers.all())
                | Q(author__in=user.subscribed_journalists.all())
            )
            .select_related('author', 'publisher')
            .distinct()
        )


class ArticleDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a single article with role checks."""

    serializer_class = ArticleSerializer
    queryset = Article.objects.all().select_related('author', 'publisher')
    permission_classes = [IsAuthenticated, ReadOnlyOrEditorJournalist]

    def get_object(self):
        """Apply reader visibility and journalist ownership rules."""
        article = super().get_object()
        user = self.request.user
        if self.request.method == 'GET':
            if user.role == RoleChoices.READER and not article.approved:
                raise PermissionDenied(
                    'Readers can only view approved articles.'
                )
            return article

        if (
            user.role == RoleChoices.JOURNALIST
            and article.author_id != user.id
        ):
            raise PermissionDenied(
                'Journalists can only modify their own articles.'
            )
        return article


class NewsletterListCreateAPIView(generics.ListCreateAPIView):
    """List newsletters or create one as a journalist or editor."""

    serializer_class = NewsletterSerializer
    queryset = Newsletter.objects.all().select_related('author')
    permission_classes = [IsAuthenticated, ReadOnlyOrEditorJournalist]

    def perform_create(self, serializer):
        """Set the authenticated user as the newsletter author."""
        serializer.save(author=self.request.user)


class NewsletterDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a newsletter with ownership checks."""

    serializer_class = NewsletterSerializer
    queryset = Newsletter.objects.all().select_related('author')
    permission_classes = [IsAuthenticated, ReadOnlyOrEditorJournalist]

    def get_object(self):
        """Journalists may change only newsletters they authored."""
        newsletter = super().get_object()
        user = self.request.user
        mutating = self.request.method in {'PUT', 'PATCH', 'DELETE'}
        if mutating and user.role == RoleChoices.JOURNALIST:
            if newsletter.author_id != user.id:
                raise PermissionDenied(
                    'Journalists can only modify their own newsletters.'
                )
        return newsletter


class InternalApprovedLogAPIView(APIView):
    """Receive approval payloads posted by the article signal."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Store a payload when the internal API key is valid."""
        provided_key = request.headers.get('X-Internal-Key')
        if provided_key != settings.INTERNAL_API_KEY:
            return Response(
                {'detail': 'Forbidden.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        article_id = request.data.get('article_id')
        if not article_id:
            return Response(
                {'detail': 'article_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        article = get_object_or_404(Article, pk=article_id)
        log = ApprovedArticleLog.objects.create(
            article=article,
            payload=request.data,
        )
        return Response(
            {'id': log.id, 'detail': 'Logged.'},
            status=status.HTTP_201_CREATED,
        )

