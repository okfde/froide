import base64

from django.db import models
from django.utils.translation import gettext_lazy as _

from .request import FoiRequest


class DeferredMessageManager(models.Manager):
    def get_publicbody_for_email(self, email):
        deferreds = self.get_queryset().filter(
            sender=email, request__isnull=False,
            delivered=True, spam=False
        ).order_by('-timestamp')
        if deferreds:
            deferred = deferreds[0]
            return deferred.request.public_body


class DeferredMessage(models.Model):
    recipient = models.CharField(max_length=255, blank=True)
    sender = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    request = models.ForeignKey(FoiRequest, null=True, blank=True,
        on_delete=models.CASCADE)
    mail = models.TextField(blank=True)
    spam = models.NullBooleanField(null=True, default=False)
    delivered = models.BooleanField(default=False)

    objects = DeferredMessageManager()

    class Meta:
        ordering = ('timestamp',)
        get_latest_by = 'timestamp'
        verbose_name = _('Undelivered Message')
        verbose_name_plural = _('Undelivered Messages')

    def __str__(self):
        return _("Undelievered Message to %(recipient)s (%(request)s)") % {
            'recipient': self.recipient,
            'request': self.request
        }

    def encoded_mail(self):
        return base64.b64decode(self.mail)

    def decoded_mail(self):
        return self.encoded_mail().decode('utf-8', 'ignore')

    def redeliver(self, request):
        from ..tasks import process_mail

        self.request = request
        self.delivered = True
        self.spam = False
        self.save()
        mail = base64.b64decode(self.mail)
        mail = mail.replace(self.recipient.encode('utf-8'),
                            self.request.secret_address.encode('utf-8'))
        process_mail.delay(mail, manual=True)
