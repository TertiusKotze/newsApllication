"""Automated tests for HTML workflows and the news REST API."""

from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    ApprovedArticleLog,
    Article,
    Newsletter,
    Publisher,
    RoleChoices,
    User,
)


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class FrontendFlowTestCase(TestCase):
    """Cover registration, navigation, and role-based HTML pages."""

    def test_login_page_has_register_link(self):
        """The login template must point new users to registration."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, reverse('register'))

    def test_register_page_has_login_link(self):
        """The registration template must link back to login."""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, reverse('login'))

    def test_reader_can_register_from_frontend(self):
        """A valid registration form creates and logs in a reader."""
        response = self.client.post(
            reverse('register'),
            {
                'username': 'newreader',
                'email': 'newreader@example.com',
                'role': RoleChoices.READER,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
        )
        self.assertRedirects(response, reverse('approved-articles'))
        user = User.objects.get(username='newreader')
        self.assertEqual(user.role, RoleChoices.READER)
        self.assertTrue(user.groups.filter(name='Reader').exists())

    def test_register_page_offers_role_choice(self):
        """The registration form must let users pick their account type."""
        response = self.client.get(reverse('register'))
        self.assertContains(response, 'name="role"')
        for role in RoleChoices.values:
            self.assertContains(response, f'value="{role}"')

    def test_journalist_and_editor_can_register(self):
        """Journalist and editor sign-ups join their matching group."""
        for role, group_name in (
            (RoleChoices.JOURNALIST, 'Journalist'),
            (RoleChoices.EDITOR, 'Editor'),
        ):
            username = f'new{role}'
            self.client.post(
                reverse('register'),
                {
                    'username': username,
                    'email': f'{username}@example.com',
                    'role': role,
                    'password1': 'StrongPass123!',
                    'password2': 'StrongPass123!',
                },
            )
            self.client.logout()
            user = User.objects.get(username=username)
            self.assertEqual(user.role, role)
            self.assertTrue(user.groups.filter(name=group_name).exists())

    def test_invalid_role_is_rejected(self):
        """An unknown role value must not create an account."""
        response = self.client.post(
            reverse('register'),
            {
                'username': 'hacker',
                'email': 'hacker@example.com',
                'role': 'admin',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(username='hacker').exists())

    def test_invalid_registration_is_rejected(self):
        """Mismatched passwords must not create an account."""
        response = self.client.post(
            reverse('register'),
            {
                'username': 'badreader',
                'email': 'bad@example.com',
                'role': RoleChoices.READER,
                'password1': 'StrongPass123!',
                'password2': 'DifferentPass123!',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(username='badreader').exists())

    def test_global_nav_contains_core_links(self):
        """Anonymous visitors see login, register, and article links."""
        response = self.client.get(reverse('login'))
        self.assertContains(response, reverse('approved-articles'))
        self.assertContains(response, reverse('login'))
        self.assertContains(response, reverse('register'))

    def test_editor_sees_pending_link_in_global_nav(self):
        """Editors get a pending-review link in the shared navbar."""
        editor = User.objects.create_user(
            username='editor-nav',
            email='editor-nav@example.com',
            password='pass12345',
            role=RoleChoices.EDITOR,
        )
        self.client.force_login(editor)
        response = self.client.get(reverse('approved-articles'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, reverse('pending-articles'))

    def test_reader_can_open_subscriptions_page(self):
        """Readers can manage publisher and journalist follows."""
        reader = User.objects.create_user(
            username='sub-reader',
            email='sub-reader@example.com',
            password='pass12345',
            role=RoleChoices.READER,
        )
        self.client.force_login(reader)
        response = self.client.get(reverse('subscriptions'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reader_cannot_open_pending_queue(self):
        """Readers are blocked from the editor moderation page."""
        reader = User.objects.create_user(
            username='blocked-reader',
            email='blocked-reader@example.com',
            password='pass12345',
            role=RoleChoices.READER,
        )
        self.client.force_login(reader)
        response = self.client.get(reverse('pending-articles'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_journalist_can_create_article_from_frontend(self):
        """Journalists can submit HTML articles that stay unapproved."""
        journalist = User.objects.create_user(
            username='html-journalist',
            email='html-journalist@example.com',
            password='pass12345',
            role=RoleChoices.JOURNALIST,
        )
        self.client.force_login(journalist)
        response = self.client.post(
            reverse('article-create'),
            {
                'title': 'Front-end story',
                'content': 'Written from the HTML form.',
                'publisher': '',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        article = Article.objects.get(title='Front-end story')
        self.assertFalse(article.approved)
        self.assertEqual(article.author, journalist)


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class NewsAPITestCase(APITestCase):
    """Cover REST authentication, subscriptions, and role permissions."""

    def setUp(self):
        """Create users, a publisher, and a mix of articles."""
        self.reader = User.objects.create_user(
            username='reader1',
            email='reader1@example.com',
            password='pass12345',
            role=RoleChoices.READER,
        )
        self.editor = User.objects.create_user(
            username='editor1',
            email='editor1@example.com',
            password='pass12345',
            role=RoleChoices.EDITOR,
        )
        self.journalist = User.objects.create_user(
            username='journalist1',
            email='journalist1@example.com',
            password='pass12345',
            role=RoleChoices.JOURNALIST,
        )
        self.other_journalist = User.objects.create_user(
            username='journalist2',
            email='journalist2@example.com',
            password='pass12345',
            role=RoleChoices.JOURNALIST,
        )
        self.publisher = Publisher.objects.create(
            name='Daily Scope',
            description='Publisher',
        )
        self.publisher.editors.add(self.editor)
        self.publisher.journalists.add(self.journalist)
        self.publisher_pending = Article.objects.create(
            title='Pending Publisher Story',
            content='Awaiting editor',
            author=self.journalist,
            publisher=self.publisher,
            approved=False,
        )
        self.approved_subscribed_article = Article.objects.create(
            title='Subscribed Publisher Article',
            content='Publisher content',
            author=self.journalist,
            publisher=self.publisher,
            approved=True,
        )
        self.approved_unsubscribed_article = Article.objects.create(
            title='Unsubscribed Article',
            content='Not subscribed',
            author=self.other_journalist,
            approved=True,
        )
        self.pending_article = Article.objects.create(
            title='Pending Story',
            content='Pending content',
            author=self.journalist,
            approved=False,
        )
        self.reader.subscribed_publishers.add(self.publisher)
        self.reader.subscribed_journalists.add(self.journalist)

    def authenticate(self, user):
        """Authenticate API requests as the given user."""
        self.client.force_authenticate(user=user)

    def test_unauthenticated_article_list_is_rejected(self):
        """Anonymous clients cannot list articles."""
        response = self.client.get(reverse('api-articles'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_token_grants_access(self):
        """A valid JWT can be used against the articles endpoint."""
        token_response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'reader1', 'password': 'pass12345'},
            format='json',
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        access = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get(reverse('api-articles'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_jwt_is_rejected(self):
        """A forged token must not unlock the API."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not-a-real-token')
        response = self.client.get(reverse('api-articles'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reader_can_only_get_subscribed_articles(self):
        """Subscribed endpoint returns only followed sources."""
        self.authenticate(self.reader)
        response = self.client.get(reverse('api-articles-subscribed'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item['title'] for item in response.data}
        self.assertIn('Subscribed Publisher Article', titles)
        self.assertNotIn('Unsubscribed Article', titles)

    def test_editor_cannot_use_subscribed_endpoint(self):
        """The subscription feed is limited to reader accounts."""
        self.authenticate(self.editor)
        response = self.client.get(reverse('api-articles-subscribed'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reader_can_retrieve_approved_article(self):
        """Readers may open an approved article by id."""
        self.authenticate(self.reader)
        response = self.client.get(
            reverse(
                'api-article-detail',
                kwargs={'pk': self.approved_subscribed_article.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Subscribed Publisher Article')

    def test_reader_cannot_retrieve_pending_article(self):
        """Readers must not see unapproved copy via the API."""
        self.authenticate(self.reader)
        response = self.client.get(
            reverse(
                'api-article-detail',
                kwargs={'pk': self.pending_article.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reader_cannot_create_article(self):
        """Readers are forbidden from POSTing articles."""
        self.authenticate(self.reader)
        response = self.client.post(
            reverse('api-articles'),
            {
                'title': 'Reader post',
                'content': 'Should fail',
                'approved': False,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_journalist_can_create_article(self):
        """Journalists can create an unapproved article."""
        self.authenticate(self.journalist)
        response = self.client.post(
            reverse('api-articles'),
            {
                'title': 'Journalist Post',
                'content': 'Created by journalist',
                'publisher': self.publisher.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Article.objects.get(title='Journalist Post')
        self.assertFalse(created.approved)

    def test_editor_cannot_create_article(self):
        """Editors update and delete articles but cannot create them."""
        self.authenticate(self.editor)
        response = self.client.post(
            reverse('api-articles'),
            {
                'title': 'Editor Post',
                'content': 'Should fail',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def _approve_put(self, article, publisher_id):
        """PUT approved=True for ``article`` as the authenticated user."""
        return self.client.put(
            reverse('api-article-detail', kwargs={'pk': article.id}),
            {
                'title': article.title,
                'content': article.content,
                'publisher': publisher_id,
                'approved': True,
            },
            format='json',
        )

    def test_editor_can_approve_publisher_article(self):
        """A publisher's editor can approve that publisher's article."""
        self.authenticate(self.editor)
        with patch('news.signals.requests.post') as mocked_post:
            response = self._approve_put(
                self.publisher_pending, self.publisher.id
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.publisher_pending.refresh_from_db()
        self.assertTrue(self.publisher_pending.approved)
        mocked_post.assert_called_once()

    def test_editor_of_other_publisher_cannot_approve(self):
        """Editors outside the publisher are refused."""
        outsider = User.objects.create_user(
            username='outsider', email='outsider@example.com',
            password='pass12345', role=RoleChoices.EDITOR,
        )
        self.authenticate(outsider)
        response = self._approve_put(
            self.publisher_pending, self.publisher.id
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_editor_cannot_approve_independent_article(self):
        """Independent articles are approved by their author only."""
        self.authenticate(self.editor)
        response = self._approve_put(self.pending_article, None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journalist_can_approve_own_independent_article(self):
        """Independent journalists publish their own finished drafts."""
        self.authenticate(self.journalist)
        with patch('news.signals.requests.post'):
            response = self._approve_put(self.pending_article, None)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending_article.refresh_from_db()
        self.assertTrue(self.pending_article.approved)

    def test_journalist_cannot_approve_publisher_article(self):
        """Publisher articles need an editor, not the journalist."""
        self.authenticate(self.journalist)
        response = self._approve_put(
            self.publisher_pending, self.publisher.id
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journalist_cannot_edit_another_authors_article(self):
        """Ownership is enforced on journalist updates."""
        self.authenticate(self.journalist)
        response = self.client.put(
            reverse(
                'api-article-detail',
                kwargs={'pk': self.approved_unsubscribed_article.id},
            ),
            {
                'title': 'Hijacked',
                'content': 'Should fail',
                'publisher': None,
                'approved': False,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_delete_article(self):
        """Editors may delete any article."""
        self.authenticate(self.editor)
        response = self.client.delete(
            reverse(
                'api-article-detail',
                kwargs={'pk': self.approved_unsubscribed_article.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_newsletter_create_and_reader_read_only_behavior(self):
        """Journalists create newsletters; readers cannot update them."""
        self.authenticate(self.journalist)
        create_response = self.client.post(
            reverse('api-newsletters'),
            {
                'title': 'Weekly Digest',
                'description': 'Highlights',
                'articles': [self.approved_subscribed_article.id],
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        newsletter_id = create_response.data['id']
        self.authenticate(self.reader)
        list_response = self.client.get(reverse('api-newsletters'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        update_response = self.client.put(
            reverse(
                'api-newsletter-detail',
                kwargs={'pk': newsletter_id},
            ),
            {
                'title': 'Tampered',
                'description': 'Should not work',
                'articles': [],
            },
            format='json',
        )
        self.assertEqual(
            update_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_editor_can_delete_newsletter(self):
        """Editors can remove a newsletter."""
        newsletter = Newsletter.objects.create(
            title='To remove',
            description='Temp',
            author=self.journalist,
        )
        self.authenticate(self.editor)
        response = self.client.delete(
            reverse(
                'api-newsletter-detail',
                kwargs={'pk': newsletter.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch('news.signals.send_mail')
    @patch('news.signals.requests.post')
    def test_signal_side_effects_fire_on_approval(
        self,
        mocked_post,
        mocked_send_mail,
    ):
        """Approving an article emails subscribers and posts internally."""
        self.authenticate(self.editor)
        response = self._approve_put(
            self.publisher_pending, self.publisher.id
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(mocked_send_mail.called)
        self.assertTrue(mocked_post.called)

    def test_internal_approved_endpoint_requires_key(self):
        """The log endpoint rejects missing keys and accepts a valid key."""
        payload = {
            'article_id': self.approved_subscribed_article.id,
            'title': self.approved_subscribed_article.title,
        }
        forbidden = self.client.post(
            reverse('api-approved-log'),
            payload,
            format='json',
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        allowed = self.client.post(
            reverse('api-approved-log'),
            payload,
            format='json',
            HTTP_X_INTERNAL_KEY=settings.INTERNAL_API_KEY,
        )
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ApprovedArticleLog.objects.count(), 1)

    def test_internal_approved_endpoint_requires_article_id(self):
        """A payload without article_id is a client error."""
        response = self.client.post(
            reverse('api-approved-log'),
            {'title': 'Missing id'},
            format='json',
            HTTP_X_INTERNAL_KEY=settings.INTERNAL_API_KEY,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journalist_role_helpers_return_none_for_reader_fields(self):
        """Journalist accounts expose None for reader-only helpers."""
        self.assertIsNone(self.journalist.reader_publisher_subscriptions())
        self.assertIsNone(self.journalist.reader_journalist_subscriptions())
        self.assertIsNone(self.reader.independent_articles())
        self.assertIsNone(self.reader.independent_newsletters())



class RegistrationAndPublisherTests(TestCase):
    """Unique emails, publisher registration and staff management."""

    def _register(self, **overrides):
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'role': RoleChoices.READER,
            'password1': 'Str0ng!Pass99',
            'password2': 'Str0ng!Pass99',
        }
        data.update(overrides)
        return self.client.post(reverse('register'), data)

    def test_duplicate_email_rejected_case_insensitive(self):
        """A second account cannot reuse an email in any letter case."""
        self._register()
        self.client.logout()
        response = self._register(username='other', email='NEW@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertEqual(User.objects.count(), 1)

    def test_publisher_registration_creates_publication(self):
        """Registering as publisher creates an owned publication."""
        self._register(
            username='pubco', email='pub@example.com',
            role=RoleChoices.PUBLISHER, publisher_name='PubCo',
        )
        publisher = Publisher.objects.get(name='PubCo')
        self.assertEqual(publisher.owner.username, 'pubco')
        self.assertTrue(
            publisher.owner.groups.filter(name='Publisher').exists()
        )

    def test_publisher_registration_requires_name(self):
        """Publisher accounts must name their publication."""
        response = self._register(role=RoleChoices.PUBLISHER)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_publisher_adds_and_removes_staff(self):
        """Publishers manage their own editors and journalists."""
        owner = User.objects.create_user(
            username='owner', email='owner@example.com',
            password='pass12345', role=RoleChoices.PUBLISHER,
        )
        publisher = Publisher.objects.create(name='Mine', owner=owner)
        editor = User.objects.create_user(
            username='ed', email='ed@example.com',
            password='pass12345', role=RoleChoices.EDITOR,
        )
        journalist = User.objects.create_user(
            username='jo', email='jo@example.com',
            password='pass12345', role=RoleChoices.JOURNALIST,
        )
        self.client.force_login(owner)
        self.client.post(
            reverse('publisher-manage'),
            {'editors': [editor.pk], 'journalists': [journalist.pk]},
        )
        self.assertTrue(publisher.editors.filter(pk=editor.pk).exists())
        self.assertTrue(
            publisher.journalists.filter(pk=journalist.pk).exists()
        )
        self.client.post(reverse('publisher-manage'), {'editors': [editor.pk]})
        self.assertFalse(publisher.journalists.exists())

    def test_non_publisher_cannot_manage_staff(self):
        """Other roles get 403 on the management page."""
        reader = User.objects.create_user(
            username='rd', email='rd@example.com',
            password='pass12345', role=RoleChoices.READER,
        )
        self.client.force_login(reader)
        response = self.client.get(reverse('publisher-manage'))
        self.assertEqual(response.status_code, 403)

    def test_independent_journalist_approves_via_html(self):
        """Independent authors approve their own article in the UI."""
        journalist = User.objects.create_user(
            username='indie', email='indie@example.com',
            password='pass12345', role=RoleChoices.JOURNALIST,
        )
        article = Article.objects.create(
            title='Indie', content='Draft', author=journalist,
        )
        self.client.force_login(journalist)
        with patch('news.signals.requests.post'):
            self.client.post(reverse('approve-article', args=[article.pk]))
        article.refresh_from_db()
        self.assertTrue(article.approved)
