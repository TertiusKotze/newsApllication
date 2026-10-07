"""Domain models for users, publishers, articles, and newsletters."""

from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.db import models


class RoleChoices(models.TextChoices):
    """Supported application roles mapped to Django auth groups."""

    READER = 'reader', 'Reader'
    EDITOR = 'editor', 'Editor'
    JOURNALIST = 'journalist', 'Journalist'
    PUBLISHER = 'publisher', 'Publisher'


class User(AbstractUser):
    """Custom user with a role, subscriptions, and reverse publications.

    Reader-only fields:
        subscribed_publishers, subscribed_journalists

    Journalist-only fields (reverse relations):
        articles, newsletters

    Non-reader accounts keep subscription relations empty. Non-journalist
    accounts must not author articles, so those reverse relations stay
    unused and helper methods return ``None``.
    """

    email = models.EmailField(
        'email address',
        unique=True,
        help_text='Must be unique; used for password resets and emails.',
    )
    role = models.CharField(max_length=20, choices=RoleChoices.choices)
    subscribed_publishers = models.ManyToManyField(
        'Publisher',
        related_name='subscribers',
        blank=True,
        help_text='Publishers followed by reader accounts.',
    )
    subscribed_journalists = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='reader_subscribers',
        blank=True,
        limit_choices_to={'role': RoleChoices.JOURNALIST},
        help_text='Independent journalists followed by reader accounts.',
    )

    def clean(self):
        """Block readers from staff flags and duplicate emails."""
        super().clean()
        if self.role == RoleChoices.READER and (
            self.is_staff or self.is_superuser
        ):
            raise ValidationError('Readers cannot be staff users.')
        if self.email and User.objects.filter(
            email__iexact=self.email
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                {'email': 'An account with this email already exists.'}
            )

    def save(self, *args, **kwargs):
        """Persist the user, then keep role-specific fields consistent."""
        if self.email:
            # Normalise so "A@x.com" and "a@x.com" count as duplicates.
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
        # Only readers subscribe; clear reader-only relations otherwise.
        if self.role != RoleChoices.READER:
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()
        self.assign_group_from_role()

    def assign_group_from_role(self):
        """Place the user in exactly one group matching their role."""
        role_group_map = {
            RoleChoices.READER: 'Reader',
            RoleChoices.EDITOR: 'Editor',
            RoleChoices.JOURNALIST: 'Journalist',
            RoleChoices.PUBLISHER: 'Publisher',
        }
        target_group_name = role_group_map.get(self.role)
        if not target_group_name:
            return

        self.groups.clear()
        group, _ = Group.objects.get_or_create(name=target_group_name)
        self.groups.add(group)

    def reader_publisher_subscriptions(self):
        """Return publisher subscriptions, or None for non-readers."""
        if self.role != RoleChoices.READER:
            return None
        return self.subscribed_publishers.all()

    def reader_journalist_subscriptions(self):
        """Return journalist subscriptions, or None for non-readers."""
        if self.role != RoleChoices.READER:
            return None
        return self.subscribed_journalists.all()

    def independent_articles(self):
        """Return independently published articles, or None."""
        if self.role != RoleChoices.JOURNALIST:
            return None
        return self.articles.filter(publisher__isnull=True)

    def independent_newsletters(self):
        """Return newsletters authored by this journalist, or None."""
        if self.role != RoleChoices.JOURNALIST:
            return None
        return self.newsletters.all()

    def __str__(self):
        return self.username


class Publisher(models.Model):
    """A publication owned by a Publisher user, staffed by its choice."""

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    owner = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_publisher',
        limit_choices_to={'role': RoleChoices.PUBLISHER},
        help_text='Publisher account that manages editors/journalists.',
    )
    editors = models.ManyToManyField(
        User,
        related_name='publisher_editor_for',
        blank=True,
        limit_choices_to={'role': RoleChoices.EDITOR},
    )
    journalists = models.ManyToManyField(
        User,
        related_name='publisher_journalist_for',
        blank=True,
        limit_choices_to={'role': RoleChoices.JOURNALIST},
    )

    def __str__(self):
        return self.name


class Article(models.Model):
    """A news article authored by a journalist, optionally for a publisher.

    Independent articles leave ``publisher`` empty and are approved by
    their author. Publisher articles are approved by that publisher's
    editors.
    """

    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='articles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        """Ensure only journalists author articles."""
        super().clean()
        if not self.author_id:
            return
        if self.author.role != RoleChoices.JOURNALIST:
            raise ValidationError(
                'Only journalists can be article authors.'
            )

    @property
    def is_independent(self):
        """True when the article is not filed under a publisher."""
        return self.publisher_id is None

    def can_be_approved_by(self, user):
        """Return True when ``user`` may approve this article.

        * Independent articles: only the authoring journalist approves
          (they decide when the piece is finished).
        * Publisher articles: only editors of that publisher approve.
        """
        if not user or not user.is_authenticated or self.approved:
            return False
        if self.is_independent:
            return (
                user.role == RoleChoices.JOURNALIST
                and self.author_id == user.id
            )
        return (
            user.role == RoleChoices.EDITOR
            and self.publisher.editors.filter(pk=user.pk).exists()
        )

    def __str__(self):
        return self.title


class Newsletter(models.Model):
    """A curated collection of articles created by journalists or editors."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='newsletters',
    )
    articles = models.ManyToManyField(
        Article,
        related_name='newsletters',
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        """Restrict newsletter authorship to journalists and editors."""
        super().clean()
        if not self.author_id:
            return
        allowed = {RoleChoices.JOURNALIST, RoleChoices.EDITOR}
        if self.author.role not in allowed:
            raise ValidationError(
                'Only journalists or editors can author newsletters.'
            )

    def __str__(self):
        return self.title


class ApprovedArticleLog(models.Model):
    """Internal log of payloads posted to ``/api/approved/``."""

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='approval_logs',
    )
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return f'Approved log #{self.pk} for article {self.article_id}'

