"""Create demo accounts, a publication, articles and a newsletter.

Usage:  python manage.py seed_demo
Safe to run more than once (uses get_or_create).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from news.models import Article, Newsletter, Publisher, RoleChoices, User

DEMO_USERS = [
    # username, email, role, password
    ('tkpublishing', 'publisher@tkpublishing.local',
     RoleChoices.PUBLISHER, 'Publish@99'),
    ('tertius', 'tertius@news.local', RoleChoices.JOURNALIST, 'Journalist@99'),
    ('editor1', 'editor1@news.local', RoleChoices.EDITOR, 'Editor@99'),
    ('reader1', 'reader1@news.local', RoleChoices.READER, 'Reader@99'),
]

APPROVED_ARTICLES = [
    ('Local Council Approves New Cycling Lanes',
     'The city council voted unanimously to add 20 km of protected '
     'cycling lanes over the next two years.', True),
    ('Tech Start-ups Boom in Cape Town',
     'A new report shows record investment in Cape Town based '
     'technology start-ups this quarter.', False),
]

HUMOROUS_PENDING = [
    ('Local Cat Elected Mayor, Promises Nap Breaks for All',
     'In a landslide victory, Whiskers the tabby has been elected mayor. '
     'Her first policy: mandatory 3pm naps and a sunbeam in every office.',
     False),
    ('Man Finally Reads Terms and Conditions, Discovers He Owns a Yacht',
     'After 14 hours of scrolling, a Pretoria man reached clause 847 and '
     'learned he had accidentally been gifted a yacht in 2019.', True),
    ('Wi-Fi Router Demands Union Representation',
     'Tired of being restarted "just to see if it helps", a home router '
     'has filed a complaint with the labour department.', False),
]


class Command(BaseCommand):
    help = 'Seed demo users, TKPublishing, articles and a newsletter.'

    @transaction.atomic
    def handle(self, *args, **options):
        users = {}
        for username, email, role, password in DEMO_USERS:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'role': role},
            )
            user.email, user.role = email, role
            user.set_password(password)
            user.save()
            users[username] = user

        publisher, _ = Publisher.objects.get_or_create(
            name='TKPublishing',
            defaults={'description': 'Independent South African news.'},
        )
        publisher.owner = users['tkpublishing']
        publisher.save()
        publisher.editors.add(users['editor1'])
        publisher.journalists.add(users['tertius'])

        approved = []
        for title, content, for_publisher in APPROVED_ARTICLES:
            article, _ = Article.objects.get_or_create(
                title=title,
                defaults={
                    'content': content,
                    'author': users['tertius'],
                    'publisher': publisher if for_publisher else None,
                },
            )
            if not article.approved:
                article.approved = True
                article.save()
            approved.append(article)

        for title, content, for_publisher in HUMOROUS_PENDING:
            Article.objects.get_or_create(
                title=title,
                defaults={
                    'content': content,
                    'author': users['tertius'],
                    'publisher': publisher if for_publisher else None,
                    'approved': False,
                },
            )

        newsletter, _ = Newsletter.objects.get_or_create(
            title='Weekly Roundup',
            defaults={
                'description': 'The best stories of the week.',
                'author': users['tertius'],
            },
        )
        newsletter.articles.set(approved)

        users['reader1'].subscribed_publishers.add(publisher)
        users['reader1'].subscribed_journalists.add(users['tertius'])
        self.stdout.write(self.style.SUCCESS('Demo data ready.'))

