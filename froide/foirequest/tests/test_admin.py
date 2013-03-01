from __future__ import with_statement

from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.test.client import RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.storage import default_storage

from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest, FoiAttachment, DeferredMessage
from froide.foirequest.admin import (FoiRequestAdmin,
    FoiAttachmentAdmin, DeferredMessageAdmin)


class AdminActionTest(TestCase):

    def setUp(self):
        self.site = factories.make_world()
        self.admin_site = AdminSite()
        self.request_admin = FoiRequestAdmin(FoiRequest,
            self.admin_site)
        self.attachment_admin = FoiAttachmentAdmin(FoiAttachment,
            self.admin_site)
        self.factory = RequestFactory()
        self.user = User.objects.get(username='sw')
        self.user.is_superuser = True

    def test_mark_same_as(self):
        req = self.factory.post('/', {})
        req.user = self.user
        factories.FoiRequestFactory(site=self.site)
        factories.FoiRequestFactory(site=self.site)
        frs = FoiRequest.objects.all()[:2]
        result = self.request_admin.mark_same_as(req, frs)
        self.assertEqual(result.status_code, 200)

        same_as = factories.FoiRequestFactory(site=self.site)
        same_as.save()

        req = self.factory.post('/', {'req_id': same_as.id})
        req.user = self.user
        req._messages = default_storage(req)

        frs = FoiRequest.objects.filter(
            id__in=[frs[0].id, frs[1].id])

        result = self.request_admin.mark_same_as(req, frs)
        self.assertIsNone(result)
        same_as = FoiRequest.objects.get(id=same_as.id)
        self.assertEqual(same_as.same_as_count, 2)
        frs = list(frs)
        frs[0] = FoiRequest.objects.get(id=frs[0].id)
        frs[1] = FoiRequest.objects.get(id=frs[1].id)
        self.assertEqual(frs[0].same_as, same_as)
        self.assertEqual(frs[1].same_as, same_as)

    def test_tag_all(self):
        req = self.factory.post('/', {})
        req.user = self.user
        factories.FoiRequestFactory(site=self.site)
        factories.FoiRequestFactory(site=self.site)
        frs = FoiRequest.objects.all()[:2]
        result = self.request_admin.tag_all(req, frs)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(frs[0].tags.count(), 0)
        self.assertEqual(frs[1].tags.count(), 0)

        req = self.factory.post('/', {'tags': 'one, two'})
        req.user = self.user
        req._messages = default_storage(req)

        frs = FoiRequest.objects.filter(
            id__in=[frs[0].id, frs[1].id])

        result = self.request_admin.tag_all(req, frs)
        self.assertIsNone(result)
        frs = list(frs)
        frs[0] = FoiRequest.objects.get(id=frs[0].id)
        frs[1] = FoiRequest.objects.get(id=frs[1].id)
        self.assertEqual(frs[0].tags.count(), 2)
        self.assertEqual(frs[1].tags.count(), 2)
        self.assertEqual(set([t.name for t in frs[0].tags.all()]), set(['one', 'two']))

    def check_attribute_change_action(self, klass, factory,
         admin_action, attr, initial, final,
         factory_extra=None):
        if factory_extra is None:
            d = {}
        else:
            d = factory_extra

        d.update({attr: initial})
        r0 = factory(**d)
        r0.save()
        r1 = factory(**d)
        r1.save()
        rs = klass.objects.filter(
            id__in=[r0.id, r1.id])

        req = self.factory.post('/', {})
        req.user = self.user
        req._messages = default_storage(req)

        result = admin_action(req, rs)
        self.assertIsNone(result)
        rs = klass.objects.filter(id__in=[
            r0.id, r1.id
        ])
        for r in rs:
            self.assertEqual(getattr(r, attr), final)

    def test_mark_checked(self):
        self.check_attribute_change_action(
            FoiRequest,
            factories.FoiRequestFactory,
            self.request_admin.mark_checked,
            'checked', False, True,
            factory_extra={'site': self.site}
        )

    def test_mark_not_foi(self):
        self.check_attribute_change_action(
            FoiRequest,
            factories.FoiRequestFactory,
            self.request_admin.mark_not_foi,
            'is_foi', True, False,
            factory_extra={'site': self.site}
        )

    def test_approve(self):
        self.check_attribute_change_action(
            FoiAttachment,
            factories.FoiAttachmentFactory,
            self.attachment_admin.approve,
            'approved', False, True
        )

    def test_cannot_approve(self):
        self.check_attribute_change_action(
            FoiAttachment,
            factories.FoiAttachmentFactory,
            self.attachment_admin.cannot_approve,
            'can_approve', True, False
        )


class RedeliverAdminActionTest(TestCase):
    def setUp(self):
        self.site = factories.make_world()
        self.admin_site = AdminSite()
        self.admin = DeferredMessageAdmin(DeferredMessage,
            self.admin_site)
        self.factory = RequestFactory()
        self.user = User.objects.get(username='sw')
        self.user.is_superuser = True

    def test_redeliver(self):
        foireq = FoiRequest.objects.all()[0]
        dm = factories.DeferredMessageFactory()
        dm.save()
        req = self.factory.post('/', {})
        req.user = self.user

        result = self.admin.redeliver(req,
                DeferredMessage.objects.filter(
                    id__in=[dm.id]))
        self.assertEqual(result.status_code, 200)

        req = self.factory.post('/', {
            'req_id': foireq.id
        })
        req.user = self.user
        req._messages = default_storage(req)

        result = self.admin.redeliver(req,
                DeferredMessage.objects.filter(
                    id__in=[dm.id]))
        self.assertIsNone(result)

        dm = DeferredMessage.objects.get(id=dm.id)
        self.assertEqual(dm.request, foireq)
