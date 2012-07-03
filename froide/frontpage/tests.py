from __future__ import with_statement

from datetime import datetime, timedelta

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import translation
from django.contrib.sites.models import Site

from froide.foirequest.models import FoiRequest

from .models import FeaturedRequest


class RequestTest(TestCase):
    fixtures = ['auth_profile.json', 'publicbody.json', 'foirequest.json']

    def setUp(self):
        translation.activate(settings.LANGUAGE_CODE)

    def test_featured_requests(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        some_foireq = FoiRequest.objects.all()[0]
        title = "Awesome Request"
        FeaturedRequest.objects.create(request=some_foireq,
            title=title,
            timestamp=datetime.now(),
            text="",
            url="",
        site=Site.objects.get_current())
        title2 = "Awesomer Request"
        FeaturedRequest.objects.create(request=some_foireq,
            title=title2,
            timestamp=datetime.now() + timedelta(days=1),
            text="",
            url="",
            site=Site.objects.get_current())
        response = self.client.get(reverse('index') + "?bust_cache=true")
        self.assertEqual(response.status_code, 200)
        self.assertIn(title2, response.content)
