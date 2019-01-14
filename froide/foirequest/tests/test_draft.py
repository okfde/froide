from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape
from django.contrib.auth import get_user_model

from froide.publicbody.models import PublicBody
from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest, RequestDraft

User = get_user_model()


class RequestDraftTest(TestCase):

    def setUp(self):
        factories.make_world()
        self.pb = PublicBody.objects.all()[0]

    def test_draft_not_loggedin(self):
        post = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            "first_name": "Stefan", "last_name": "Wehrmeyer",
            "user_email": "dummy@example.com",
            "terms": "on",
            'save_draft': 'true',
            "publicbody": str(self.pb.pk)
        }
        response = self.client.post(reverse('foirequest-make_request'), post)
        self.assertEqual(response.status_code, 302)

        user = User.objects.filter(email=post['user_email']).get()
        self.assertFalse(user.is_active)
        self.assertTrue(RequestDraft.objects.count() == 0)

    def test_draft_not_loggedin_setting_draft(self):
        draft = factories.RequestDraftFactory.create()
        post = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            "first_name": "Stefan", "last_name": "Wehrmeyer",
            "user_email": "dummy@example.com",
            "terms": "on",
            'save_draft': 'true',
            'draft': str(draft.id)
        }
        response = self.client.post(reverse('foirequest-make_request',
                kwargs={'publicbody_slug': self.pb.slug}), post)
        self.assertEqual(response.status_code, 400)

    def test_draft_logged_in(self):
        ok = self.client.login(email='info@fragdenstaat.de', password='froide')
        self.assertTrue(ok)

        post = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            'public': 'on',
            'reference': 'test:abcdefg',
            'save_draft': 'true',
            'publicbody': str(self.pb.pk)
        }
        response = self.client.post(reverse('foirequest-make_request',
                kwargs={'publicbody_slug': self.pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        drafts_url = reverse('account-drafts')
        self.assertTrue(response['Location'].endswith(drafts_url))

        user = User.objects.filter(email='info@fragdenstaat.de').get()
        req = FoiRequest.objects.filter(title=post['subject'])
        self.assertTrue(req.count() == 0)

        draft = RequestDraft.objects.get(user=user)
        self.assertEqual(draft.subject, post['subject'])
        self.assertEqual(draft.body, post['body'])
        self.assertEqual(draft.public, True)
        self.assertEqual(draft.full_text, False)
        self.assertEqual(draft.reference, post['reference'])
        self.assertEqual(list(draft.publicbodies.all()), [self.pb])

        response = self.client.get(drafts_url)
        self.assertContains(response, post['subject'])
        self.assertContains(response, escape(draft.get_absolute_url()))

        post['draft'] = str(draft.pk)
        post['subject'] = 'Another subject'
        post['publicbody'] = str(self.pb.pk)
        response = self.client.post(reverse('foirequest-make_request'), post)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RequestDraft.objects.all().count(), 1)

        draft = RequestDraft.objects.get(user=user)
        self.assertEqual(draft.subject, post['subject'])
        self.assertEqual(draft.body, post['body'])
        self.assertEqual(draft.public, True)
        self.assertEqual(draft.full_text, False)
        self.assertEqual(draft.reference, post['reference'])
        self.assertEqual(list(draft.publicbodies.all()), [self.pb])

        del post['save_draft']
        response = self.client.post(reverse('foirequest-make_request'), post)
        self.assertEqual(response.status_code, 302)
        draft = RequestDraft.objects.get(id=draft.pk)
        req = FoiRequest.objects.get(title=post['subject'])
        self.assertEqual(draft.request, req)
        self.assertIsNone(draft.project)

        self.client.logout()
        self.client.login(email="dummy@example.org", password="froide")

        response = self.client.post(reverse('foirequest-delete_draft'),
                                    {'draft_id': draft.pk})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(RequestDraft.objects.all().count() == 1)

        ok = self.client.login(email='info@fragdenstaat.de', password='froide')
        response = self.client.post(reverse('foirequest-delete_draft'),
                                    {'draft_id': draft.pk})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(drafts_url))
        self.assertTrue(RequestDraft.objects.all().count() == 0)

    def test_draft_make_request(self):
        ok = self.client.login(email='info@fragdenstaat.de', password='froide')
        self.assertTrue(ok)
        user = User.objects.get(email='info@fragdenstaat.de')
        draft = factories.RequestDraftFactory(user=user)
        draft.publicbodies.add(self.pb)
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_draft_token(self):
        user = User.objects.get(email='info@fragdenstaat.de')
        post = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            "first_name": "Stefan", "last_name": "Wehrmeyer",
            "user_email": user.email,
            "terms": "on",
            'publicbody': str(self.pb.pk),
            'hide_editing': '1',
            'hide_similar': '1'
        }
        response = self.client.post(reverse('foirequest-make_request',
                kwargs={'publicbody_slug': self.pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        draft = RequestDraft.objects.all()[0]
        self.assertIsNone(draft.user)
        self.assertTrue(bool(draft.token))

        ok = self.client.login(email='info@fragdenstaat.de', password='froide')
        self.assertTrue(ok)

        response = self.client.get(
            reverse('foirequest-claim_draft', kwargs={
                'token': str(draft.token)
            })
        )
        self.assertEqual(response.status_code, 302)
        # import ipdb ; ipdb.set_trace()
        self.assertTrue(response['Location'].endswith(
            draft.get_absolute_url())
        )
        draft = RequestDraft.objects.get(id=draft.id)
        self.assertEqual(draft.user, user)
        flags = draft.flags
        self.assertEqual(flags['hide_editing'], True)
        self.assertEqual(flags['hide_similar'], True)
        url = draft.get_absolute_public_url()
        self.assertIn('hide_similar=1', url)
