# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('foirequest', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FoiRequestFollower',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.CharField(max_length=255, blank=True)),
                ('confirmed', models.BooleanField(default=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Timestamp of Following')),
                ('request', models.ForeignKey(verbose_name='Freedom of Information Request', to='foirequest.FoiRequest', on_delete=django.db.models.deletion.CASCADE)),
                ('user', models.ForeignKey(verbose_name='User', blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'ordering': ('timestamp',),
                'get_latest_by': 'timestamp',
                'verbose_name': 'Request Follower',
                'verbose_name_plural': 'Request Followers',
            },
        ),
    ]
