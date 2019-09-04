from urllib.parse import urlencode

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.postgres.fields import JSONField
from django.utils.functional import cached_property

from froide.publicbody.models import PublicBody

from .request import FoiRequest, FoiProject


def convert_flag(val):
    if isinstance(val, bool):
        return str(int(val))
    return str(val)


class RequestDraft(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.CASCADE
    )
    token = models.UUIDField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    save_date = models.DateTimeField(auto_now=True)

    publicbodies = models.ManyToManyField(PublicBody)

    subject = models.CharField(_("subject"), max_length=255, blank=True)
    body = models.TextField(_("body"), blank=True)

    full_text = models.BooleanField(default=False)
    public = models.BooleanField(default=True)
    reference = models.CharField(max_length=255, blank=True)
    law_type = models.CharField(max_length=255, blank=True)
    flags = JSONField(blank=True, default=dict)

    request = models.ForeignKey(FoiRequest, null=True, blank=True,
                                on_delete=models.SET_NULL)
    project = models.ForeignKey(FoiProject, null=True, blank=True,
                                on_delete=models.SET_NULL)

    class Meta:
        verbose_name = _('request draft')
        verbose_name_plural = _('request drafts')
        ordering = ['-save_date']

    def __str__(self):
        return _('Draft "{subject}" by {user}').format(
            subject=self.subject,
            user=self.user
        )

    @property
    def request_or_project(self):
        return self.request or self.project

    @property
    def title(self):
        return self.subject

    @cached_property
    def is_multi_request(self):
        return self.publicbodies.all().count() > 1

    def get_absolute_url(self):
        return reverse('foirequest-make_draftrequest', kwargs={'pk': self.id})

    def get_initial(self):
        context = {
            'draft': self.pk,
            'subject': self.subject,
            'body': self.body,
            'public': self.public,
            'full_text': self.full_text,
        }
        if self.reference:
            context['reference'] = self.reference
        if self.flags:
            context.update(self.flags)
        return context

    def get_url_params(self):
        return {k: convert_flag(v) for k, v in self.get_initial().items()}

    def get_absolute_public_url(self):
        pb_ids = '+'.join(str(pb.pk) for pb in self.publicbodies.all())
        url_kwargs = {}
        if pb_ids:
            url_kwargs = {
                'publicbody_ids': pb_ids
            }
        url = reverse('foirequest-make_request', kwargs=url_kwargs)
        context = self.get_url_params()
        query = urlencode({k: str(v).encode('utf-8') for k, v in context.items()})
        return '%s?%s' % (url, query)
