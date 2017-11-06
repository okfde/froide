# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.manager
import froide.foirequest.models


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeferredMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('recipient', models.CharField(max_length=255, blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('mail', models.TextField(blank=True)),
                ('spam', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('timestamp',),
                'get_latest_by': 'timestamp',
                'verbose_name': 'Undelivered Message',
                'verbose_name_plural': 'Undelivered Messages',
            },
        ),
        migrations.CreateModel(
            name='FoiAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('file', models.FileField(upload_to=froide.foirequest.models.attachment.upload_to, max_length=255, verbose_name='File')),
                ('size', models.IntegerField(null=True, verbose_name='Size', blank=True)),
                ('filetype', models.CharField(max_length=100, verbose_name='File type', blank=True)),
                ('format', models.CharField(max_length=100, verbose_name='Format', blank=True)),
                ('can_approve', models.BooleanField(default=True, verbose_name='User can approve')),
                ('approved', models.BooleanField(default=False, verbose_name='Approved')),
                ('is_redacted', models.BooleanField(default=False, verbose_name='Is redacted')),
                ('is_converted', models.BooleanField(default=False, verbose_name='Is converted')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Attachment',
                'verbose_name_plural': 'Attachments',
            },
        ),
        migrations.CreateModel(
            name='FoiEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('public', models.BooleanField(default=True, verbose_name='Is Public?')),
                ('event_name', models.CharField(max_length=255, verbose_name='Event Name')),
                ('timestamp', models.DateTimeField(verbose_name='Timestamp')),
                ('context_json', models.TextField(verbose_name='Context JSON')),
            ],
            options={
                'ordering': ('-timestamp',),
                'verbose_name': 'Request Event',
                'verbose_name_plural': 'Request Events',
            },
        ),
        migrations.CreateModel(
            name='FoiMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sent', models.BooleanField(default=True, verbose_name='has message been sent?')),
                ('is_response', models.BooleanField(default=True, verbose_name='Is this message a response?')),
                ('is_postal', models.BooleanField(default=False, verbose_name='Postal?')),
                ('is_escalation', models.BooleanField(default=False, verbose_name='Escalation?')),
                ('content_hidden', models.BooleanField(default=False, verbose_name='Content hidden?')),
                ('sender_email', models.CharField(max_length=255, verbose_name='From Email', blank=True)),
                ('sender_name', models.CharField(max_length=255, verbose_name='From Name', blank=True)),
                ('recipient', models.CharField(max_length=255, null=True, verbose_name='Recipient', blank=True)),
                ('recipient_email', models.CharField(max_length=255, null=True, verbose_name='Recipient Email', blank=True)),
                ('status', models.CharField(default=None, choices=[(b'awaiting_user_confirmation', 'Awaiting user confirmation'), (b'publicbody_needed', 'Public Body needed'), (b'awaiting_publicbody_confirmation', 'Awaiting Public Body confirmation'), (b'awaiting_response', 'Awaiting response'), (b'awaiting_classification', 'Request awaits classification'), (b'asleep', 'Request asleep'), (b'resolved', 'Request resolved')], max_length=50, blank=True, null=True, verbose_name='Status')),
                ('timestamp', models.DateTimeField(verbose_name='Timestamp', blank=True)),
                ('subject', models.CharField(max_length=255, verbose_name='Subject', blank=True)),
                ('subject_redacted', models.CharField(max_length=255, verbose_name='Redacted Subject', blank=True)),
                ('plaintext', models.TextField(null=True, verbose_name='plain text', blank=True)),
                ('plaintext_redacted', models.TextField(null=True, verbose_name='redacted plain text', blank=True)),
                ('html', models.TextField(null=True, verbose_name='HTML', blank=True)),
                ('original', models.TextField(verbose_name='Original', blank=True)),
                ('redacted', models.BooleanField(default=False, verbose_name='Was Redacted?')),
                ('not_publishable', models.BooleanField(default=False, verbose_name='Not publishable')),
            ],
            options={
                'ordering': ('timestamp',),
                'get_latest_by': 'timestamp',
                'verbose_name': 'Freedom of Information Message',
                'verbose_name_plural': 'Freedom of Information Messages',
            },
        ),
        migrations.CreateModel(
            name='FoiRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(unique=True, max_length=255, verbose_name='Slug')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('summary', models.TextField(verbose_name='Summary', blank=True)),
                ('status', models.CharField(max_length=50, verbose_name='Status', choices=[(b'awaiting_user_confirmation', 'Awaiting user confirmation'), (b'publicbody_needed', 'Public Body needed'), (b'awaiting_publicbody_confirmation', 'Awaiting Public Body confirmation'), (b'awaiting_response', 'Awaiting response'), (b'awaiting_classification', 'Request awaits classification'), (b'asleep', 'Request asleep'), (b'resolved', 'Request resolved')])),
                ('resolution', models.CharField(blank=True, max_length=50, verbose_name='Resolution', choices=[(b'successful', 'Request Successful'), (b'partially_successful', 'Request partially successful'), (b'not_held', 'Information not held'), (b'refused', 'Request refused'), (b'user_withdrew_costs', 'Request was withdrawn due to costs'), (b'user_withdrew', 'Request was withdrawn')])),
                ('public', models.BooleanField(default=True, verbose_name='published?')),
                ('visibility', models.SmallIntegerField(default=0, verbose_name='Visibility', choices=[(0, 'Invisible'), (1, 'Visible to Requester'), (2, 'Public')])),
                ('first_message', models.DateTimeField(null=True, verbose_name='Date of first message', blank=True)),
                ('last_message', models.DateTimeField(null=True, verbose_name='Date of last message', blank=True)),
                ('resolved_on', models.DateTimeField(null=True, verbose_name='Resolution date', blank=True)),
                ('due_date', models.DateTimeField(null=True, verbose_name='Due Date', blank=True)),
                ('secret_address', models.CharField(unique=True, max_length=255, verbose_name='Secret address', db_index=True)),
                ('secret', models.CharField(max_length=100, verbose_name='Secret', blank=True)),
                ('same_as_count', models.IntegerField(default=0, verbose_name='Identical request count')),
                ('costs', models.FloatField(default=0.0, verbose_name='Cost of Information')),
                ('refusal_reason', models.CharField(max_length=1024, verbose_name='Refusal reason', blank=True)),
                ('checked', models.BooleanField(default=False, verbose_name='checked')),
                ('is_foi', models.BooleanField(default=True, verbose_name='is FoI request')),
            ],
            options={
                'ordering': ('last_message',),
                'get_latest_by': 'last_message',
                'verbose_name': 'Freedom of Information Request',
                'verbose_name_plural': 'Freedom of Information Requests',
                'permissions': (('see_private', 'Can see private requests'),),
            },
            managers=[
                ('non_filtered_objects', django.db.models.manager.Manager()),
                ('objects', froide.foirequest.models.request.FoiRequestManager()),
                ('published', froide.foirequest.models.request.PublishedFoiRequestManager()),
                ('published_not_foi', froide.foirequest.models.request.PublishedNotFoiRequestManager()),
            ],
        ),
        migrations.CreateModel(
            name='PublicBodySuggestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Timestamp of Suggestion')),
                ('reason', models.TextField(default=b'', verbose_name='Reason this Public Body fits the request', blank=True)),
            ],
            options={
                'ordering': ('timestamp',),
                'get_latest_by': 'timestamp',
                'verbose_name': 'Public Body Suggestion',
                'verbose_name_plural': 'Public Body Suggestions',
            },
        ),
        migrations.CreateModel(
            name='TaggedFoiRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content_object', models.ForeignKey(to='foirequest.FoiRequest', on_delete=django.db.models.deletion.CASCADE)),
                ('tag', models.ForeignKey(related_name='foirequest_taggedfoirequest_items', to='taggit.Tag', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'verbose_name': 'FoI Request Tag',
                'verbose_name_plural': 'FoI Request Tags',
            },
        ),
    ]
