from __future__ import with_statement

import re
from datetime import datetime, timedelta
import os

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.core import mail
from django.utils import translation
from django.contrib.sites.models import Site
# from django.utils import timezone

from frontpage.models import FeaturedRequest
from foirequest.models import FoiRequest


class RequestTest(TestCase):
    fixtures = ['auth_profile.json', 'publicbody.json', 'foirequest.json']

    def setUp(self):
        translation.activate(settings.LANGUAGE_CODE)

    def test_featured_requests(self):
        return
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        some_foireq = FoiRequest.objects.all()[0]
        title = "Awesome Request"
        FeaturedRequest.objects.create(request=some_foireq,
            title=title,
            timestamp=timezone.now(),
            text="",
            url="",
        site=Site.objects.get_current())
        title2 = "Awesomer Request"
        FeaturedRequest.objects.create(request=some_foireq,
            title=title2,
            timestamp=timezone.now() + timedelta(days=1),
            text="",
            url="",
            site=Site.objects.get_current())
        response = self.client.get(reverse('index')+"?bust_cache=true")
        self.assertEqual(response.status_code, 200)
        self.assertIn(title2, response.content)
