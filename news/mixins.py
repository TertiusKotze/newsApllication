"""Reusable access-control mixins for role-based HTML views."""

from django.contrib.auth.mixins import UserPassesTestMixin

from .models import RoleChoices


class RoleRequiredMixin(UserPassesTestMixin):
    """Allow access only when the authenticated user has an allowed role.

    Set ``allowed_roles`` on the view to a collection of ``RoleChoices``
    values. Unauthenticated users are handled by ``LoginRequiredMixin``,
    which should be listed before this mixin.
    """

    allowed_roles = ()

    def test_func(self):
        """Return True when the current user has an allowed role."""
        user = self.request.user
        return bool(
            user.is_authenticated and user.role in self.allowed_roles
        )


class EditorRequiredMixin(RoleRequiredMixin):
    """Restrict a view to editor accounts."""

    allowed_roles = (RoleChoices.EDITOR,)


class JournalistRequiredMixin(RoleRequiredMixin):
    """Restrict a view to journalist accounts."""

    allowed_roles = (RoleChoices.JOURNALIST,)


class JournalistOrEditorRequiredMixin(RoleRequiredMixin):
    """Restrict a view to journalist and editor accounts."""

    allowed_roles = (RoleChoices.JOURNALIST, RoleChoices.EDITOR)


class ReaderRequiredMixin(RoleRequiredMixin):
    """Restrict a view to reader accounts."""

    allowed_roles = (RoleChoices.READER,)


class PublisherRequiredMixin(RoleRequiredMixin):
    """Restrict a view to publisher accounts."""

    allowed_roles = (RoleChoices.PUBLISHER,)


