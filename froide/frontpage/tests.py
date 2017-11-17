from __future__ import with_statement

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from django.utils import translation, timezone

from froide.foirequest.models import FoiRequest
from froide.foirequest.tests.factories import make_world

from .models import FeaturedRequest


class RequestTest(TestCase):

    def setUp(self):
        self.site = make_world()
        translation.activate(settings.LANGUAGE_CODE)

    def test_featured_requests(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        some_foireq = FoiRequest.objects.all()[0]
        title = "Awesome Request"
        FeaturedRequest.objects.create(request=some_foireq,
            title=title,
            timestamp=timezone.now(),
            text="",
            url="",
            site=self.site
        )
        title2 = "Awesomer Request"
        FeaturedRequest.objects.create(request=some_foireq,
            title=title2,
            timestamp=timezone.now() + timedelta(days=1),
            text="",
            url="",
            site=self.site)
        response = self.client.get(reverse('index') + "?bust_cache=true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, title2)
