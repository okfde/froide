# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import django.db.models.manager
import django.utils.timezone
from django.conf import settings
import django.db.models.deletion
import froide.publicbody.models
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FoiLaw',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('slug', models.SlugField(max_length=255, verbose_name='Slug')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('long_description', models.TextField(verbose_name='Website Text', blank=True)),
                ('created', models.DateField(null=True, verbose_name='Creation Date', blank=True)),
                ('updated', models.DateField(null=True, verbose_name='Updated Date', blank=True)),
                ('request_note', models.TextField(verbose_name='request note', blank=True)),
                ('meta', models.BooleanField(default=False, verbose_name='Meta Law')),
                ('letter_start', models.TextField(verbose_name='Start of Letter', blank=True)),
                ('letter_end', models.TextField(verbose_name='End of Letter', blank=True)),
                ('priority', models.SmallIntegerField(default=3, verbose_name='Priority')),
                ('url', models.CharField(max_length=255, verbose_name='URL', blank=True)),
                ('max_response_time', models.IntegerField(default=30, null=True, verbose_name='Maximal Response Time', blank=True)),
                ('max_response_time_unit', models.CharField(default=b'day', max_length=32, verbose_name='Unit of Response Time', blank=True, choices=[(b'day', 'Day(s)'), (b'working_day', 'Working Day(s)'), (b'month_de', 'Month(s) (DE)')])),
                ('refusal_reasons', models.TextField(verbose_name='Possible Refusal Reasons, one per line, e.g \xa7X.Y: Privacy Concerns', blank=True)),
                ('email_only', models.BooleanField(default=False, verbose_name='E-Mail only')),
                ('combined', models.ManyToManyField(to='publicbody.FoiLaw', verbose_name='Combined Laws', blank=True)),
            ],
            options={
                'verbose_name': 'Freedom of Information Law',
                'verbose_name_plural': 'Freedom of Information Laws',
            },
        ),
        migrations.CreateModel(
            name='Jurisdiction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('slug', models.SlugField(max_length=255, verbose_name='Slug')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('hidden', models.BooleanField(default=False, verbose_name='Hidden')),
                ('rank', models.SmallIntegerField(default=1)),
            ],
            options={
                'verbose_name': 'Jurisdiction',
                'verbose_name_plural': 'Jurisdictions',
            },
        ),
        migrations.CreateModel(
            name='PublicBody',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('other_names', models.TextField(default=b'', verbose_name='Other names', blank=True)),
                ('slug', models.SlugField(max_length=255, verbose_name='Slug')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('url', models.URLField(max_length=500, null=True, verbose_name='URL', blank=True)),
                ('depth', models.SmallIntegerField(default=0)),
                ('classification', models.CharField(max_length=255, verbose_name='Classification', blank=True)),
                ('classification_slug', models.SlugField(max_length=255, verbose_name='Classification Slug', blank=True)),
                ('email', models.EmailField(max_length=254, null=True, verbose_name='Email', blank=True)),
                ('contact', models.TextField(verbose_name='Contact', blank=True)),
                ('address', models.TextField(verbose_name='Address', blank=True)),
                ('website_dump', models.TextField(null=True, verbose_name='Website Dump', blank=True)),
                ('request_note', models.TextField(verbose_name='request note', blank=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Updated at')),
                ('confirmed', models.BooleanField(default=True, verbose_name='confirmed')),
                ('number_of_requests', models.IntegerField(default=0, verbose_name='Number of requests')),
                ('_created_by', models.ForeignKey(related_name='public_body_creators', on_delete=django.db.models.deletion.SET_NULL, default=1, blank=True, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Created by')),
                ('_updated_by', models.ForeignKey(related_name='public_body_updaters', on_delete=django.db.models.deletion.SET_NULL, default=1, blank=True, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Updated by')),
                ('jurisdiction', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Jurisdiction', blank=True, to='publicbody.Jurisdiction', null=True)),
                ('laws', models.ManyToManyField(to='publicbody.FoiLaw', verbose_name='Freedom of Information Laws')),
                ('parent', models.ForeignKey(related_name='children', on_delete=django.db.models.deletion.SET_NULL, default=None, blank=True, to='publicbody.PublicBody', null=True)),
                ('root', models.ForeignKey(related_name='descendants', on_delete=django.db.models.deletion.SET_NULL, default=None, blank=True, to='publicbody.PublicBody', null=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, default=1, verbose_name='Site', to='sites.Site', null=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Public Body',
                'verbose_name_plural': 'Public Bodies',
            },
            managers=[
                ('non_filtered_objects', django.db.models.manager.Manager()),
                ('published', froide.publicbody.models.PublicBodyManager()),
            ],
        ),
        migrations.CreateModel(
            name='PublicBodyTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('slug', models.SlugField(unique=True, max_length=100, verbose_name='Slug')),
                ('is_topic', models.BooleanField(default=False, verbose_name='as topic')),
                ('rank', models.SmallIntegerField(default=0, verbose_name='rank')),
            ],
            options={
                'verbose_name': 'Public Body Tag',
                'verbose_name_plural': 'Public Body Tags',
            },
        ),
        migrations.CreateModel(
            name='TaggedPublicBody',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content_object', models.ForeignKey(to='publicbody.PublicBody', on_delete=django.db.models.deletion.CASCADE)),
                ('tag', models.ForeignKey(related_name='publicbodies', to='publicbody.PublicBodyTag', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'verbose_name': 'Tagged Public Body',
                'verbose_name_plural': 'Tagged Public Bodies',
            },
        ),
        migrations.AddField(
            model_name='publicbody',
            name='tags',
            field=taggit.managers.TaggableManager(to='publicbody.PublicBodyTag', through='publicbody.TaggedPublicBody', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='foilaw',
            name='jurisdiction',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Jurisdiction', blank=True, to='publicbody.Jurisdiction', null=True),
        ),
        migrations.AddField(
            model_name='foilaw',
            name='mediator',
            field=models.ForeignKey(related_name='mediating_laws', on_delete=django.db.models.deletion.SET_NULL, default=None, blank=True, to='publicbody.PublicBody', null=True, verbose_name='Mediator'),
        ),
        migrations.AddField(
            model_name='foilaw',
            name='site',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, default=1, verbose_name='Site', to='sites.Site', null=True),
        ),
    ]
