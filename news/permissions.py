"""Role-based permission classes for the news REST API."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import RoleChoices


class IsReader(BasePermission):
    """Allow access only to authenticated reader accounts."""

    def has_permission(self, request, view):
        """Return True only for an authenticated reader."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == RoleChoices.READER
        )


class IsJournalist(BasePermission):
    """Allow access only to authenticated journalist accounts."""

    def has_permission(self, request, view):
        """Return True only for an authenticated journalist."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == RoleChoices.JOURNALIST
        )


class IsEditor(BasePermission):
    """Allow access only to authenticated editor accounts."""

    def has_permission(self, request, view):
        """Return True only for an authenticated editor."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == RoleChoices.EDITOR
        )


class IsEditorOrJournalist(BasePermission):
    """Allow editors and journalists to access a write endpoint."""

    def has_permission(self, request, view):
        """Return True for an authenticated editor or journalist."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role in {
                RoleChoices.EDITOR,
                RoleChoices.JOURNALIST,
            }
        )


class ReadOnlyOrEditorJournalist(BasePermission):
    """Allow any authenticated user to read; staff roles to write."""

    def has_permission(self, request, view):
        """Allow reads for any logged-in user and writes for staff roles."""
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role in {RoleChoices.EDITOR, RoleChoices.JOURNALIST}
