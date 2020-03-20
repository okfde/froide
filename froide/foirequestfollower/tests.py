import re
import json

import factory

from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from django_comments import get_model, get_form

from froide.foirequest.models import FoiRequest
from froide.foirequest.tests import factories
from froide.foirequest.tests.test_api import OAuthAPIMixin

from .models import FoiRequestFollower
from .utils import run_batch_update

User = get_user_model()
Comment = get_model()
CommentForm = get_form()


class FoiRequestFollowerFactory(factory.DjangoModelFactory):
    class Meta:
        model = FoiRequestFollower

    request = factory.SubFactory(factories.FoiRequestFactory)
    user = factory.SubFactory(factories.UserFactory)
    email = ''
    confirmed = True


class FoiRequestFollowerTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()

    def test_following(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(username='sw')
        self.client.login(email='info@fragdenstaat.de', password='froide')
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
        # Can't follow my own requests
        self.assertEqual(response.status_code, 400)
        followers = FoiRequestFollower.objects.filter(request=req, user=user)
        self.assertEqual(followers.count(), 0)
        self.client.logout()
        user = User.objects.get(username='dummy')
        self.client.login(email='dummy@example.org', password='froide')
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        follower = FoiRequestFollower.objects.get(request=req, user=user)
        self.assertEqual(len(mail.outbox), 0)
        # Make second message postal message
        # So there's no notification to requester about sent mail
        req.messages[1].kind = 'post'
        req.message_sent.send(sender=req, message=req.messages[1])
        self.assertEqual(len(mail.outbox), 1)
        mes = mail.outbox[0]
        match = re.search(r'/%d/(\w+)/' % follower.pk, mes.body)
        check = match.group(1)
        response = self.client.get(
            reverse('foirequestfollower-confirm_unfollow',
                kwargs={'follow_id': follower.id,
                        'check': "a" * 32}))
        self.assertEqual(response.status_code, 302)
        follower = FoiRequestFollower.objects.get(request=req, user=user)
        response = self.client.get(
            reverse('foirequestfollower-confirm_unfollow',
                kwargs={'follow_id': follower.id,
                        'check': check}))
        self.assertEqual(response.status_code, 302)
        try:
            FoiRequestFollower.objects.get(request=req, user=user)
        except FoiRequestFollower.DoesNotExist:
            pass
        else:
            self.assertTrue(False)

    def test_unfollowing(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(username='dummy')
        self.client.login(email='dummy@example.org', password='froide')
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        follower = FoiRequestFollower.objects.filter(request=req, user=user).count()
        self.assertEqual(follower, 1)
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        follower = FoiRequestFollower.objects.filter(request=req, user=user).count()
        self.assertEqual(follower, 0)

    def test_email_following(self):
        req = FoiRequest.objects.all()[0]
        email = 'test@example.org'
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}), {
                    'email': email
                })
        self.assertEqual(response.status_code, 302)
        follower = FoiRequestFollower.objects.get(
            request=req, user=None, email=email)
        self.assertFalse(follower.confirmed)
        self.assertEqual(len(mail.outbox), 1)

        # Bad secret in URL
        response = self.client.get(
            reverse('foirequestfollower-confirm_follow',
                kwargs={'follow_id': follower.id,
                        'check': "a" * 32}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            FoiRequestFollower.objects.filter(
                request=req, user=None, email=email, confirmed=True
            ).exists()
        )
        mes = mail.outbox[0]
        match = re.search(r'/%d/(\w+)/' % follower.pk, mes.body)
        check = match.group(1)

        response = self.client.get(
            reverse('foirequestfollower-confirm_follow',
                kwargs={'follow_id': follower.id,
                        'check': check}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            FoiRequestFollower.objects.filter(
                request=req, user=None, email=email, confirmed=True
            ).exists()
        )

    def test_user_email_following(self):
        req = FoiRequest.objects.all()[0]
        user = User.objects.get(username='dummy')
        email = user.email
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}), {
                    'email': email
                })
        self.assertEqual(response.status_code, 302)
        follower = FoiRequestFollower.objects.get(
            request=req, user=None, email=email)
        self.assertFalse(follower.confirmed)
        self.assertEqual(len(mail.outbox), 1)

        mes = mail.outbox[0]
        match = re.search(r'/%d/(\w+)/' % follower.pk, mes.body)
        check = match.group(1)

        response = self.client.get(
            reverse('foirequestfollower-confirm_follow',
                kwargs={'follow_id': follower.id,
                        'check': check}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            FoiRequestFollower.objects.filter(
                request=req, user=user, email='', confirmed=True
            ).exists()
        )

    def test_updates(self):
        mail.outbox = []
        req = FoiRequest.objects.all()[0]
        comment_user = factories.UserFactory()
        user = User.objects.get(username='dummy')
        self.client.login(email='dummy@example.org', password='froide')
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        ok = self.client.login(username=comment_user.email, password='froide')
        self.assertTrue(ok)

        mes = list(req.messages)[-1]
        d = {
            'comment': 'This is my comment',
        }

        f = CommentForm(mes)
        d.update(f.initial)
        self.client.post(reverse("comments-post-comment"), d)
        run_batch_update()
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to[0], req.user.email)
        self.assertEqual(mail.outbox[1].to[0], user.email)

    def test_updates_avoid(self):
        mail.outbox = []
        req = FoiRequest.objects.all()[0]
        dummy_user = User.objects.get(username='dummy')
        req2 = factories.FoiRequestFactory.create(
            site=self.site, user=req.user)
        mes = list(req.messages)[-1]
        mes2 = factories.FoiMessageFactory.create(request=req2)
        ok = self.client.login(username=req.user.email, password='froide')
        self.assertTrue(ok)
        d = {
            'comment': 'This is my comment',
        }
        f = CommentForm(mes)
        d.update(f.initial)
        self.client.post(reverse("comments-post-comment"), d)

        run_batch_update(update_requester=False)

        self.assertEqual(len(mail.outbox), 0)

        mail.outbox = []
        self.client.logout()

        def do_follow(req, email):
            ok = self.client.login(email=email, password='froide')
            self.assertTrue(ok)
            response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
            self.assertEqual(response.status_code, 302)
            self.client.logout()

        def do_comment(mes, email):
            ok = self.client.login(email=email, password='froide')
            self.assertTrue(ok)
            f = CommentForm(mes)
            d.update(f.initial)
            self.client.post(
                reverse("comments-post-comment"),
                d
            )

        do_follow(req, 'dummy@example.org')
        do_comment(mes, 'info@fragdenstaat.de')

        do_follow(req2, 'dummy@example.org')
        do_comment(mes2, 'info@fragdenstaat.de')

        run_batch_update()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], dummy_user.email)

        Comment.objects.all().delete()
        mail.outbox = []

        do_comment(mes2, 'dummy@example.org')

        run_batch_update()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], req.user.email)


class ApiTest(OAuthAPIMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.accessible = FoiRequest.objects.get(user=self.test_user)
        self.inaccessible = FoiRequest.objects.get(user=self.dev_user)

        self.other = factories.FoiRequestFactory.create(
            visibility=FoiRequest.VISIBLE_TO_PUBLIC,
            user=self.dev_user,
            title='always shown'
        )

        self.following_request_url = '{}?request={},{},{}'.format(
            reverse('api:following-list'),
            self.accessible.id,
            self.inaccessible.id,
            self.other.id
        )
        self.follow_url = reverse('api:following-list')

    def test_following_requests_unauth(self):
        response = self.client.get(self.following_request_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['meta']['total_count'], 1)
        self.assertTrue(
            result['objects'][0]['request'].endswith('/request/{}/'.format(
                self.other.id
            ))
        )

    def test_following_requests_oauth_no_scope(self):
        response, result = self.api_get(self.following_request_url)
        self.assertEqual(result['meta']['total_count'], 1)
        self.assertTrue(
            result['objects'][0]['request'].endswith('/request/{}/'.format(
                self.other.id
            ))
        )

    def test_following_requests_login(self):
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.get(self.following_request_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['meta']['total_count'], 2)
        result_ids = {int(x['request'].rsplit('/')[-2]) for x in result['objects']}
        self.assertEqual(result_ids, {self.other.id, self.accessible.id})

    def test_following_requests_oauth_read_scope(self):
        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        response, result = self.api_get(self.following_request_url)
        self.assertEqual(result['meta']['total_count'], 2)
        result_ids = {int(x['request'].rsplit('/')[-2]) for x in result['objects']}
        self.assertEqual(result_ids, {self.other.id, self.accessible.id})

    def test_follow_unauth(self):
        request_ids = (
            self.accessible.id, self.inaccessible.id, self.other.id
        )
        for request_id in request_ids:
            response = self.client.post(self.follow_url, json.dumps({
                'request': request_id
            }), content_type="application/json")
            self.assertEqual(response.status_code, 401)

    def test_follow_loggedin(self):
        self.client.login(email="dummy@example.org", password="froide")
        response = self.client.post(self.follow_url, json.dumps({
            'request': self.accessible.id
        }), content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response = self.client.post(self.follow_url, json.dumps({
            'request': self.inaccessible.id
        }), content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response = self.client.post(self.follow_url, json.dumps({
            'request': self.other.id
        }), content_type="application/json")
        self.assertEqual(response.status_code, 201)

        response = self.client.get(self.follow_url)
        self.assertEqual(response.status_code, 200)

        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['meta']['total_count'], 1)
        resource_uri = result['objects'][0]['resource_uri']
        resource_uri_relative = '/'.join([''] + resource_uri.split('/')[3:])
        response = self.client.delete(
            resource_uri_relative, content_type="application/json"
        )
        self.assertEqual(response.status_code, 204)
        response = self.client.get(self.follow_url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['meta']['total_count'], 0)

    def test_follow_oauth_no_scope(self):
        self.access_token.scope = "read:user read:request"
        self.access_token.save()

        request_ids = (
            self.accessible.id, self.inaccessible.id, self.other.id
        )
        for request_id in request_ids:
            response, result = self.api_post(self.follow_url, {
                'request': request_id
            })
            self.assertEqual(response.status_code, 403)

    def test_follow_auth_with_scope(self):
        self.access_token.scope = "read:user read:request follow:request"
        self.access_token.save()

        response, result = self.api_post(self.follow_url, {
            'request': self.accessible.id
        })
        self.assertEqual(response.status_code, 400)

        response, result = self.api_post(self.follow_url, {
            'request': self.inaccessible.id
        })
        self.assertEqual(response.status_code, 400)

        response, result = self.api_post(self.follow_url, {
            'request': self.other.id
        })
        self.assertEqual(response.status_code, 201)
        response, result = self.api_get(self.follow_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result['meta']['total_count'], 1)
        resource_uri = result['objects'][0]['resource_uri']
        resource_uri_relative = '/'.join([''] + resource_uri.split('/')[3:])
        response, result = self.api_delete(
            resource_uri_relative
        )
        self.assertEqual(response.status_code, 204)
        response, result = self.api_get(self.follow_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result['meta']['total_count'], 0)

    def test_delete_other(self):
        ''' Try deleting other random things '''
        self.client.login(email="dummy@example.org", password="froide")

        ff_obj = FoiRequestFollower.objects.create(
            id=self.accessible.id,
            user=self.dev_user,
            request=self.accessible
        )

        delete_url = reverse('api:following-detail', kwargs={
            'pk': ff_obj.id
        }) + '?request={}'.format(ff_obj.id)
        response = self.client.delete(
            delete_url, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)

        delete_url = reverse('api:following-detail', kwargs={
            'pk': ff_obj.id
        })
        response = self.client.delete(
            delete_url, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
