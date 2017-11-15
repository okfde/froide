from __future__ import unicode_literals

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from froide.publicbody.models import PublicBody


@python_2_unicode_compatible
class RequestDraft(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    save_date = models.DateTimeField(auto_now=True)

    publicbodies = models.ManyToManyField(PublicBody)

    subject = models.CharField(_("subject"), max_length=255, blank=True)
    body = models.TextField(_("body"), blank=True)

    full_text = models.BooleanField(default=False)
    public = models.BooleanField(default=True)
    reference = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _('request draft')
        verbose_name_plural = _('request drafts')

    def __str__(self):
        return _('Draft "{subject}" by {user}').format(
            subject=self.subject,
            user=self.user
        )

    def get_absolute_url(self):
        pb_ids = '+'.join(str(pb.pk) for pb in self.publicbodies.all())
        url = reverse('foirequest-make_request', kwargs={
            'publicbody_ids': pb_ids
        })
        context = {
            'draft': str(self.pk),
            'subject': self.subject,
            'body': self.body,
            'public': ('1' if self.public else '0'),
            'full_text': ('1' if self.full_text else '0'),
        }
        if self.reference:
            context['ref'] = self.reference

        query = urlencode({k: v.encode('utf-8') for k, v in context.items()})
        return '%s?%s' % (url, query)
