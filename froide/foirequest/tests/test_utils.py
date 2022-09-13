from django.test import TestCase

from froide.foirequest.tests import factories
from froide.foirequest.utils import get_publicbody_for_email
from froide.publicbody.factories import FoiLawFactory, PublicBodyFactory


class FoiRequestPublicBodyInfoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mediator = PublicBodyFactory()
        cls.law = FoiLawFactory(mediator=cls.mediator)
        cls.pb1 = PublicBodyFactory()
        cls.pb1.laws.add(cls.law)
        cls.req = factories.FoiRequestFactory(public_body=cls.pb1)
        cls.sent_message = factories.FoiMessageFactory(
            request=cls.req,
            is_response=False,
            recipient_public_body=cls.pb1,
            recipient_email=cls.pb1.email,
        )
        cls.pb1_alt_email = cls.pb1.email.replace("@", ".alt@")
        cls.pb1_alt_name = "Alt-Name"
        cls.received_message = factories.FoiMessageFactory(
            request=cls.req,
            is_response=True,
            sender_public_body=cls.pb1,
            sender_email=cls.pb1_alt_email,
            sender_name=cls.pb1_alt_name,
        )

    def test_get_publicbody_for_email(self):
        pb = get_publicbody_for_email(self.pb1.email, self.req)
        self.assertEqual(pb, self.pb1)

        pb = get_publicbody_for_email(self.pb1_alt_email, self.req)
        self.assertEqual(pb, self.pb1)

        pb = get_publicbody_for_email(self.mediator.email, self.req)
        self.assertEqual(pb, self.mediator)
