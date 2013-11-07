from django.test import TestCase

from froide.foirequest.tests import factories
from froide.foirequest.templatetags.foirequest_tags import check_same_request


class TemplateTagTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_check_same_request(self):
        context = {}
        var_name = 'same_as'
        user_1 = factories.UserFactory.create()
        user_2 = factories.UserFactory.create()
        user_3 = factories.UserFactory.create()
        original = factories.FoiRequestFactory.create(user=user_1,
                                                      site=self.site)
        same_1 = factories.FoiRequestFactory.create(user=user_2,
                                                    same_as=original,
                                                    site=self.site)
        same_2 = factories.FoiRequestFactory.create(user=user_3,
                                                    same_as=original,
                                                    site=self.site)

        check_same_request(context, original, user_2, var_name)
        self.assertEqual(context[var_name], same_1)

        check_same_request(context, same_2, user_2, var_name)
        self.assertEqual(context[var_name], same_1)

        check_same_request(context, same_2, user_1, var_name)
        self.assertEqual(context[var_name], False)
