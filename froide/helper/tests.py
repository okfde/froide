from django.test import TestCase


class TestAPIDocs(TestCase):
    def test_api_docs_main(self):
        response = self.client.get('/api/v1/docs/')
        self.assertEqual(response.status_code, 200)

    def test_api_docs_resource(self):
        response = self.client.get('/api/v1/docs/resources/')
        self.assertEqual(response.status_code, 200)
