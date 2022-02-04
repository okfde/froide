from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation

from froide.account.models import User


class Command(BaseCommand):
    help = "Sends mail to all users"

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        filename = args[0]
        with open(filename) as fd:
            content = fd.read()

        subject, content = self.get_content(content)
        for user_pk in self.send_mail(subject, content):
            self.stdout.write("%s" % user_pk)

    def send_mail(self, subject, content):
        users = User.objects.filter(is_active=True)
        users = users.exclude(email="")

        for user in users.iterator():
            user.send_mail(subject, content, fail_silently=False, priority=False)
            yield user.pk

    def get_content(self, content):
        content = content.splitlines()
        subject = content[0].strip()
        content = "\n".join(content[1:]).strip()
        return subject, content
