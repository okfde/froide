from django.test import TestCase

from .text_utils import replace_email_name


class TestAPIDocs(TestCase):
    def test_api_docs_main(self):
        response = self.client.get('/api/v1/docs/')
        self.assertEqual(response.status_code, 200)

    def test_api_docs_resource(self):
        response = self.client.get('/api/v1/docs/resources/')
        self.assertEqual(response.status_code, 200)


class TestTextReplacement(TestCase):
    def test_email_name_replacement(self):
        content = 'This is a very long string with a name <and.email@adress.in> it'
        content = replace_email_name(content, 'REPLACEMENT')
        self.assertEqual(content, 'This is a very long string with a name REPLACEMENT it')
