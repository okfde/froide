from __future__ import with_statement

from django.test import TestCase

from foirequest.tasks import _process_mail
from foirequest.models import FoiRequest


class MailTest(TestCase):
    fixtures = ['publicbodies.json', "foirequest.json"]

    def test_working(self):
        with file("foirequest/tests/test_mail_01.txt") as f:
            _process_mail(f.read())
        request = FoiRequest.objects.get_by_secret_mail("s.wehrmeyer+axb4afh@fragdenstaat.de")
        messages = request.foimessage_set.all()
        assert len(messages) == 2



