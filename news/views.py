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
    SubscriptionForm,
    UserRegistrationForm,
)
from .mixins import (
    EditorRequiredMixin,
    JournalistOrEditorRequiredMixin,
    JournalistRequiredMixin,
    ReaderRequiredMixin,
)
from .models import Article, Newsletter, RoleChoices


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
    EditorRequiredMixin,
    View,
):
    """Render the moderation queue for editor accounts."""

    def get(self, request):
        """List articles that still need editorial approval."""
        pending_articles = Article.objects.filter(
            approved=False,
        ).select_related('author', 'publisher')
        return render(
            request,
            'news/pending_articles.html',
            {'articles': pending_articles},
        )


class ApproveArticleView(LoginRequiredMixin, EditorRequiredMixin, View):
    """Allow editors to approve an article from the HTML workflow."""

    def post(self, request, article_id):
        """Mark the article approved and let signals notify subscribers."""
        article = get_object_or_404(Article, pk=article_id)
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
        messages.success(
            self.request,
            'Article submitted. An editor will review it shortly.',
        )
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
