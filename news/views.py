"""HTML views for browsing, writing, moderating, and subscribing."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, UpdateView

from .api_views import (  # noqa: F401
    ArticleDetailAPIView,
    ArticleListCreateAPIView,
    ArticleSubscribedAPIView,
    InternalApprovedLogAPIView,
    NewsletterDetailAPIView,
    NewsletterListCreateAPIView,
)
from .forms import (
    ArticleForm,
    NewsletterForm,
    PublisherStaffForm,
    SubscriptionForm,
    UserRegistrationForm,
)
from .mixins import (
    JournalistOrEditorRequiredMixin,
    JournalistRequiredMixin,
    PublisherRequiredMixin,
    ReaderRequiredMixin,
)
from .models import Article, Newsletter, Publisher, RoleChoices


class ApprovedArticleListView(LoginRequiredMixin, View):
    """Render approved articles for any authenticated user."""

    def get(self, request):
        """Show the latest approved articles."""
        articles = Article.objects.filter(approved=True).select_related(
            'author',
            'publisher',
        )
        return render(
            request,
            'news/approved_articles.html',
            {'articles': articles},
        )


class ArticleDetailView(LoginRequiredMixin, View):
    """Show a single article when the user is allowed to see it."""

    def get(self, request, pk):
        """Readers only see approved articles; staff see drafts too."""
        article = get_object_or_404(
            Article.objects.select_related('author', 'publisher'),
            pk=pk,
        )
        user = request.user
        if user.role == RoleChoices.READER and not article.approved:
            raise PermissionDenied(
                'Readers can only view approved articles.'
            )
        if (
            user.role == RoleChoices.JOURNALIST
            and not article.approved
            and article.author_id != user.id
        ):
            raise PermissionDenied(
                'You can only preview your own unpublished articles.'
            )
        return render(
            request,
            'news/article_detail.html',
            {'article': article},
        )


class PendingArticleListView(
    LoginRequiredMixin,
    JournalistOrEditorRequiredMixin,
    View,
):
    """Render the approval queue for the current user.

    Editors see unapproved articles of publishers they edit for.
    Journalists see their own unapproved *independent* articles, since
    no editor oversees independent work.
    """

    def get(self, request):
        """List articles the current user is allowed to approve."""
        user = request.user
        pending = Article.objects.filter(approved=False)
        if user.role == RoleChoices.EDITOR:
            pending = pending.filter(
                publisher__in=user.publisher_editor_for.all()
            )
        else:
            pending = pending.filter(author=user, publisher__isnull=True)
        return render(
            request,
            'news/pending_articles.html',
            {'articles': pending.select_related('author', 'publisher')},
        )


class ApproveArticleView(
    LoginRequiredMixin,
    JournalistOrEditorRequiredMixin,
    View,
):
    """Approve: editors for publisher articles, authors if independent."""

    def post(self, request, article_id):
        """Mark the article approved and let signals notify subscribers."""
        article = get_object_or_404(Article, pk=article_id)
        if article.approved:
            messages.info(request, 'Article is already approved.')
            return redirect('pending-articles')
        if not article.can_be_approved_by(request.user):
            raise PermissionDenied(
                "Publisher articles are approved by that publisher's "
                'editors; independent articles by their author.'
            )
        article.approved = True
        article.save(update_fields=['approved'])
        messages.success(
            request,
            f'"{article.title}" has been approved and shared.',
        )
        return redirect('pending-articles')


class ArticleCreateView(
    LoginRequiredMixin,
    JournalistRequiredMixin,
    CreateView,
):
    """Let journalists submit a new article for editorial review."""

    model = Article
    form_class = ArticleForm
    template_name = 'news/article_form.html'
    success_url = reverse_lazy('my-articles')

    def get_form_kwargs(self):
        """Pass the current journalist into the form for publisher limits."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Attach the author and keep the article unapproved."""
        form.instance.author = self.request.user
        form.instance.approved = False
        if form.cleaned_data.get('publisher'):
            note = 'Article submitted. A publisher editor will review it.'
        else:
            note = (
                'Independent draft saved. Approve it from "Pending '
                'review" when you are ready to publish.'
            )
        messages.success(self.request, note)
        return super().form_valid(form)


class ArticleUpdateView(
    LoginRequiredMixin,
    JournalistOrEditorRequiredMixin,
    UpdateView,
):
    """Let editors, or the owning journalist, update an article."""

    model = Article
    form_class = ArticleForm
    template_name = 'news/article_form.html'
    success_url = reverse_lazy('approved-articles')

    def get_form_kwargs(self):
        """Pass the current user so publisher options stay accurate."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_object(self, queryset=None):
        """Block journalists from editing someone else's article."""
        article = super().get_object(queryset)
        user = self.request.user
        if (
            user.role == RoleChoices.JOURNALIST
            and article.author_id != user.id
        ):
            raise PermissionDenied(
                'Journalists can only edit their own articles.'
            )
        return article

    def form_valid(self, form):
        """Save edits without changing the approval flag here."""
        messages.success(self.request, 'Article updated.')
        return super().form_valid(form)


class ArticleDeleteView(
    LoginRequiredMixin,
    JournalistOrEditorRequiredMixin,
    DeleteView,
):
    """Let editors, or the owning journalist, delete an article."""

    model = Article
    template_name = 'news/article_confirm_delete.html'
    success_url = reverse_lazy('approved-articles')

    def get_object(self, queryset=None):
        """Block journalists from deleting another author's work."""
        article = super().get_object(queryset)
        user = self.request.user
        if (
            user.role == RoleChoices.JOURNALIST
            and article.author_id != user.id
        ):
            raise PermissionDenied(
                'Journalists can only delete their own articles.'
            )
        return article

    def form_valid(self, form):
        """Confirm deletion with a flash message."""
        messages.success(self.request, 'Article deleted.')
        return super().form_valid(form)


class MyArticleListView(
    LoginRequiredMixin,
    JournalistRequiredMixin,
    View,
):
    """Show the journalist their independent and publisher articles."""

    def get(self, request):
        """List every article authored by the current journalist."""
        articles = Article.objects.filter(
            author=request.user,
        ).select_related('publisher')
        return render(
            request,
            'news/my_articles.html',
            {'articles': articles},
        )


class NewsletterListView(LoginRequiredMixin, View):
    """Show newsletters to every authenticated role."""

    def get(self, request):
        """Render the newsletter catalogue."""
        newsletters = Newsletter.objects.all().select_related('author')
        return render(
            request,
            'news/newsletter_list.html',
            {'newsletters': newsletters},
        )


class NewsletterDetailView(LoginRequiredMixin, View):
    """Show one newsletter and its linked articles."""

    def get(self, request, pk):
        """Load a newsletter and the approved articles it contains."""
        newsletter = get_object_or_404(
            Newsletter.objects.select_related('author'),
            pk=pk,
        )
        articles = newsletter.articles.filter(
            approved=True,
        ).select_related('author', 'publisher')
        return render(
            request,
            'news/newsletter_detail.html',
            {'newsletter': newsletter, 'articles': articles},
        )


class NewsletterCreateView(
    LoginRequiredMixin,
    JournalistOrEditorRequiredMixin,
    CreateView,
):
    """Let journalists and editors compose a newsletter."""

    model = Newsletter
    form_class = NewsletterForm
    template_name = 'news/newsletter_form.html'
    success_url = reverse_lazy('newsletter-list')

    def form_valid(self, form):
        """Attach the current user as author."""
        form.instance.author = self.request.user
        messages.success(self.request, 'Newsletter created.')
        return super().form_valid(form)


class NewsletterUpdateView(
    LoginRequiredMixin,
    JournalistOrEditorRequiredMixin,
    UpdateView,
):
    """Let editors, or the owning journalist, update a newsletter."""

    model = Newsletter
    form_class = NewsletterForm
    template_name = 'news/newsletter_form.html'
    success_url = reverse_lazy('newsletter-list')

    def get_object(self, queryset=None):
        """Block journalists from editing someone else's newsletter."""
        newsletter = super().get_object(queryset)
        user = self.request.user
        if (
            user.role == RoleChoices.JOURNALIST
            and newsletter.author_id != user.id
        ):
            raise PermissionDenied(
                'Journalists can only edit their own newsletters.'
            )
        return newsletter

    def form_valid(self, form):
        """Confirm a successful newsletter update."""
        messages.success(self.request, 'Newsletter updated.')
        return super().form_valid(form)


class NewsletterDeleteView(
    LoginRequiredMixin,
    JournalistOrEditorRequiredMixin,
    DeleteView,
):
    """Let editors, or the owning journalist, delete a newsletter."""

    model = Newsletter
    template_name = 'news/newsletter_confirm_delete.html'
    success_url = reverse_lazy('newsletter-list')

    def get_object(self, queryset=None):
        """Block journalists from deleting another author's newsletter."""
        newsletter = super().get_object(queryset)
        user = self.request.user
        if (
            user.role == RoleChoices.JOURNALIST
            and newsletter.author_id != user.id
        ):
            raise PermissionDenied(
                'Journalists can only delete their own newsletters.'
            )
        return newsletter

    def form_valid(self, form):
        """Confirm deletion with a flash message."""
        messages.success(self.request, 'Newsletter deleted.')
        return super().form_valid(form)


class SubscriptionView(LoginRequiredMixin, ReaderRequiredMixin, View):
    """Let readers follow publishers and independent journalists."""

    def get(self, request):
        """Display the current subscription selections."""
        form = SubscriptionForm(user=request.user)
        return render(request, 'news/subscriptions.html', {'form': form})

    def post(self, request):
        """Replace the reader's subscriptions with the posted values."""
        form = SubscriptionForm(request.POST, user=request.user)
        if form.is_valid():
            request.user.subscribed_publishers.set(
                form.cleaned_data['publishers']
            )
            request.user.subscribed_journalists.set(
                form.cleaned_data['journalists']
            )
            messages.success(request, 'Your subscriptions were updated.')
            return redirect('subscriptions')
        return render(request, 'news/subscriptions.html', {'form': form})


class PublisherManageView(LoginRequiredMixin, PublisherRequiredMixin, View):
    """Let a publisher add and remove its own editors and journalists."""

    def _get_publisher(self, request):
        """Return the publication owned by the current publisher user."""
        publisher = Publisher.objects.filter(owner=request.user).first()
        if publisher is None:
            raise PermissionDenied('No publication is linked to you.')
        return publisher

    def _render(self, request, form, publisher):
        """Render the staff management page."""
        return render(
            request,
            'news/publisher_manage.html',
            {'form': form, 'publisher': publisher},
        )

    def get(self, request):
        """Show current staff with checkboxes for every candidate."""
        publisher = self._get_publisher(request)
        form = PublisherStaffForm(publisher=publisher)
        return self._render(request, form, publisher)

    def post(self, request):
        """Replace the publication's editors and journalists."""
        publisher = self._get_publisher(request)
        form = PublisherStaffForm(request.POST, publisher=publisher)
        if form.is_valid():
            publisher.editors.set(form.cleaned_data['editors'])
            publisher.journalists.set(form.cleaned_data['journalists'])
            messages.success(request, 'Publication staff updated.')
            return redirect('publisher-manage')
        return self._render(request, form, publisher)


class RegisterView(CreateView):
    """Create a Reader, Journalist, or Editor account from the front end."""

    form_class = UserRegistrationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('approved-articles')

    def form_valid(self, form):
        """Log the new user in immediately after a valid submission."""
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            f'Welcome. Your {self.object.get_role_display().lower()} '
            'account is ready.',
        )
        return response
