from __future__ import with_statement
import re

import factory

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core import mail
from django.contrib.auth.models import User
from django.contrib.comments.forms import CommentForm
from django.contrib.comments.models import Comment

from froide.foirequest.models import FoiRequest
from froide.foirequest.tests import factories

from .models import FoiRequestFollower
from .tasks import _batch_update


class FoiRequestFollowerFactory(factory.Factory):
    FACTORY_FOR = FoiRequestFollower

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
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
        # Can't follow my own requests
        self.assertEqual(response.status_code, 400)
        try:
            FoiRequestFollower.objects.get(request=req, user=user)
        except FoiRequestFollower.DoesNotExist:
            pass
        else:
            self.assertTrue(False)
        self.client.logout()
        user = User.objects.get(username='dummy')
        self.client.login(username='dummy', password='froide')
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        follower = FoiRequestFollower.objects.get(request=req, user=user)
        self.assertEqual(len(mail.outbox), 0)
        req.add_postal_reply.send(sender=req)
        self.assertEqual(len(mail.outbox), 1)
        mes = mail.outbox[0]
        match = re.search('/%d/(\w+)/' % follower.pk, mes.body)
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
        self.client.login(username='dummy', password='froide')
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

    def test_updates(self):
        mail.outbox = []
        req = FoiRequest.objects.all()[0]
        comment_user = factories.UserFactory()
        user = User.objects.get(username='dummy')
        self.client.login(username='dummy', password='froide')
        response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        self.client.login(username=comment_user.username, password='froide')
        mes = list(req.messages)[-1]
        d = {
            'name': 'Jim Bob',
            'email': 'jim.bob@example.com',
            'url': '',
            'comment': 'This is my comment',
        }

        f = CommentForm(mes)
        d.update(f.initial)
        self.client.post(reverse("comments-post-comment"), d)
        _batch_update()
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
        self.client.login(username=req.user.username, password='froide')
        d = {
            'name': 'Jim Bob',
            'email': 'jim.bob@example.com',
            'url': '',
            'comment': 'This is my comment',
        }
        f = CommentForm(mes)
        d.update(f.initial)
        self.client.post(reverse("comments-post-comment"), d)

        _batch_update(update_requester=False)

        self.assertEqual(len(mail.outbox), 0)

        mail.outbox = []
        self.client.logout()

        def do_follow(req, username):
            self.client.login(username=username, password='froide')
            response = self.client.post(reverse('foirequestfollower-follow',
                kwargs={"slug": req.slug}))
            self.assertEqual(response.status_code, 302)
            self.client.logout()

        def do_comment(mes, username):
            self.client.login(username=username, password='froide')
            f = CommentForm(mes)
            d.update(f.initial)
            self.client.post(
                reverse("comments-post-comment"),
                d
            )

        do_follow(req, 'dummy')
        do_comment(mes, 'sw')

        do_follow(req2, 'dummy')
        do_comment(mes2, 'sw')

        _batch_update()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], dummy_user.email)

        Comment.objects.all().delete()
        mail.outbox = []

        do_comment(mes2, 'dummy')

        _batch_update()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], req.user.email)
