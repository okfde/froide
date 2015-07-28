# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings
import froide.frontpage.models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('foirequest', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeaturedRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(verbose_name='Timestamp')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('text', models.TextField(verbose_name='Text')),
                ('url', models.CharField(max_length=255, verbose_name='URL', blank=True)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Featured Request', blank=True, to='foirequest.FoiRequest', null=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Site', to='sites.Site', null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='User', to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('-timestamp',),
                'get_latest_by': 'timestamp',
                'verbose_name': 'Featured Request',
                'verbose_name_plural': 'Featured Requests',
            },
            managers=[
                ('objects', froide.frontpage.models.FeaturedRequestManager()),
            ],
        ),
    ]
