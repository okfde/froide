# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0001_initial'),
        ('sites', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('foirequest', '0001_initial'),
        ('publicbody', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicbodysuggestion',
            name='public_body',
            field=models.ForeignKey(verbose_name='Public Body', to='publicbody.PublicBody', on_delete=django.db.models.deletion.CASCADE),
        ),
        migrations.AddField(
            model_name='publicbodysuggestion',
            name='request',
            field=models.ForeignKey(verbose_name='Freedom of Information Request', to='foirequest.FoiRequest', on_delete=django.db.models.deletion.CASCADE),
        ),
        migrations.AddField(
            model_name='publicbodysuggestion',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='User', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='foirequest',
            name='jurisdiction',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Jurisdiction', to='publicbody.Jurisdiction', null=True),
        ),
        migrations.AddField(
            model_name='foirequest',
            name='law',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Freedom of Information Law', blank=True, to='publicbody.FoiLaw', null=True),
        ),
        migrations.AddField(
            model_name='foirequest',
            name='public_body',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Public Body', blank=True, to='publicbody.PublicBody', null=True),
        ),
        migrations.AddField(
            model_name='foirequest',
            name='same_as',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Identical request', blank=True, to='foirequest.FoiRequest', null=True),
        ),
        migrations.AddField(
            model_name='foirequest',
            name='site',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Site', to='sites.Site', null=True),
        ),
        migrations.AddField(
            model_name='foirequest',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='foirequest.TaggedFoiRequest', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='foirequest',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='User', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='foimessage',
            name='recipient_public_body',
            field=models.ForeignKey(related_name='received_messages', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Public Body Recipient', blank=True, to='publicbody.PublicBody', null=True),
        ),
        migrations.AddField(
            model_name='foimessage',
            name='request',
            field=models.ForeignKey(verbose_name='Freedom of Information Request', to='foirequest.FoiRequest', on_delete=django.db.models.deletion.CASCADE),
        ),
        migrations.AddField(
            model_name='foimessage',
            name='sender_public_body',
            field=models.ForeignKey(related_name='send_messages', on_delete=django.db.models.deletion.SET_NULL, verbose_name='From Public Body', blank=True, to='publicbody.PublicBody', null=True),
        ),
        migrations.AddField(
            model_name='foimessage',
            name='sender_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='From User', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='foievent',
            name='public_body',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Public Body', blank=True, to='publicbody.PublicBody', null=True),
        ),
        migrations.AddField(
            model_name='foievent',
            name='request',
            field=models.ForeignKey(verbose_name='Freedom of Information Request', to='foirequest.FoiRequest', on_delete=django.db.models.deletion.CASCADE),
        ),
        migrations.AddField(
            model_name='foievent',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='User', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='foiattachment',
            name='belongs_to',
            field=models.ForeignKey(verbose_name='Belongs to request', to='foirequest.FoiMessage', null=True, on_delete=django.db.models.deletion.CASCADE),
        ),
        migrations.AddField(
            model_name='foiattachment',
            name='converted',
            field=models.ForeignKey(related_name='original_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Converted Version', blank=True, to='foirequest.FoiAttachment', null=True),
        ),
        migrations.AddField(
            model_name='foiattachment',
            name='redacted',
            field=models.ForeignKey(related_name='unredacted_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Redacted Version', blank=True, to='foirequest.FoiAttachment', null=True),
        ),
        migrations.AddField(
            model_name='deferredmessage',
            name='request',
            field=models.ForeignKey(blank=True, to='foirequest.FoiRequest', null=True, on_delete=django.db.models.deletion.CASCADE),
        ),
    ]
