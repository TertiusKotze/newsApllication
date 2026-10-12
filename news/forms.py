"""HTML forms for registration, articles, newsletters, and subscriptions."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Article, Newsletter, Publisher, RoleChoices, User


class StyledFormMixin:
    """Apply a shared CSS class to visible form widgets."""

    def _style_fields(self):
        """Add the ``input`` class used by the site stylesheet."""
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' input').strip()


class UserRegistrationForm(StyledFormMixin, UserCreationForm):
    """Register a front-end user with a chosen role and email address.

    The selected role decides which group (Reader, Journalist, or
    Editor) the user joins, and therefore which permissions they get.
    """

    email = forms.EmailField(
        required=True,
        help_text='Required. Used for newsletters and approval emails.',
    )
    role = forms.ChoiceField(
        choices=RoleChoices.choices,
        initial=RoleChoices.READER,
        label='Account type',
        help_text=(
            'Readers follow and read content, journalists write articles '
            'and newsletters, editors review publisher articles, and '
            'publishers manage their own editors and journalists.'
        ),
    )
    publisher_name = forms.CharField(
        required=False,
        max_length=200,
        label='Publication name',
        help_text='Required only for Publisher accounts.',
    )
    publisher_description = forms.CharField(
        required=False,
        label='Publication description',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        """Apply the shared field styling used by the registration page."""
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_email(self):
        """Reject email addresses already in use (case-insensitive)."""
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )
        return email

    def clean_role(self):
        """Reject any role value outside the supported choices."""
        role = self.cleaned_data.get('role')
        if role not in RoleChoices.values:
            raise forms.ValidationError('Please choose a valid account type.')
        return role

    def clean(self):
        """Require a unique publication name for publisher accounts."""
        cleaned = super().clean()
        if cleaned.get('role') == RoleChoices.PUBLISHER:
            name = (cleaned.get('publisher_name') or '').strip()
            if not name:
                self.add_error(
                    'publisher_name',
                    'Publisher accounts need a publication name.',
                )
            elif Publisher.objects.filter(name__iexact=name).exists():
                self.add_error(
                    'publisher_name',
                    'A publication with this name already exists.',
                )
            cleaned['publisher_name'] = name
        return cleaned

    def save(self, commit=True):
        """Create the user (and their publication for publisher roles)."""
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            if user.role == RoleChoices.PUBLISHER:
                Publisher.objects.create(
                    name=self.cleaned_data['publisher_name'],
                    description=self.cleaned_data.get(
                        'publisher_description', ''
                    ),
                    owner=user,
                )
        return user


class PublisherStaffForm(StyledFormMixin, forms.Form):
    """Let a publisher choose (add/remove) its editors and journalists."""

    editors = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=RoleChoices.EDITOR),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    journalists = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=RoleChoices.JOURNALIST),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, publisher=None, **kwargs):
        """Pre-select the publisher's current editors and journalists."""
        super().__init__(*args, **kwargs)
        if publisher is not None and not self.is_bound:
            self.fields['editors'].initial = list(
                publisher.editors.values_list('pk', flat=True)
            )
            self.fields['journalists'].initial = list(
                publisher.journalists.values_list('pk', flat=True)
            )


class ArticleForm(StyledFormMixin, forms.ModelForm):
    """Create or update an article without exposing approval on the form."""

    class Meta:
        model = Article
        fields = ['title', 'content', 'publisher']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 12}),
        }

    def __init__(self, *args, user=None, **kwargs):
        """Limit publisher choices to publications the journalist joins."""
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['publisher'].required = False
        self.fields['publisher'].empty_label = 'Independent article'
        self.fields['publisher'].help_text = (
            'Leave blank to publish independently, or choose a publisher '
            'you belong to.'
        )
        if user and user.role == RoleChoices.JOURNALIST:
            self.fields['publisher'].queryset = (
                user.publisher_journalist_for.all()
            )
        else:
            self.fields['publisher'].queryset = Publisher.objects.all()
        self._style_fields()

    def clean_publisher(self):
        """Prevent journalists from selecting publishers they do not join."""
        publisher = self.cleaned_data.get('publisher')
        user = self.user
        if (
            publisher
            and user
            and user.role == RoleChoices.JOURNALIST
            and not user.publisher_journalist_for.filter(
                pk=publisher.pk
            ).exists()
        ):
            raise forms.ValidationError(
                'You can only file articles under publishers you belong to.'
            )
        return publisher


class NewsletterForm(StyledFormMixin, forms.ModelForm):
    """Create or update a newsletter and attach approved articles."""

    class Meta:
        model = Newsletter
        fields = ['title', 'description', 'articles']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6}),
            'articles': forms.SelectMultiple(attrs={'size': 8}),
        }

    def __init__(self, *args, **kwargs):
        """Offer only approved articles and apply shared field styling."""
        super().__init__(*args, **kwargs)
        self.fields['articles'].queryset = Article.objects.filter(
            approved=True
        )
        self.fields['articles'].required = False
        self.fields['articles'].help_text = (
            'Hold Ctrl (or Cmd) to select multiple approved articles.'
        )
        self._style_fields()


class SubscriptionForm(StyledFormMixin, forms.Form):
    """Let readers choose publisher and journalist subscriptions."""

    publishers = forms.ModelMultipleChoiceField(
        queryset=Publisher.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Publishers',
    )
    journalists = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=RoleChoices.JOURNALIST),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Journalists',
    )

    def __init__(self, *args, user=None, **kwargs):
        """Pre-select the reader's current publisher and journalist follows."""
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields['publishers'].initial = (
                user.subscribed_publishers.values_list('pk', flat=True)
            )
            self.fields['journalists'].initial = (
                user.subscribed_journalists.values_list('pk', flat=True)
            )
