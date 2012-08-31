from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings


class Command(BaseCommand):
    help = "Counts PulbicBodies for Topics"

    def handle(self, *args, **options):
        from froide.publicbody.models import PublicBodyTopic
        translation.activate(settings.LANGUAGE_CODE)

        for topic in PublicBodyTopic.objects.all():
            topic.count = len(topic.publicbody_set.all())
            topic.save()
            self.stdout.write((u"%s: %d\n" % (topic.name, topic.count)).encode('utf-8'))
