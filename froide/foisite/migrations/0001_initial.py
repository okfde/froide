# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FoiSite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('country_code', models.CharField(max_length=5, verbose_name='Country Code')),
                ('country_name', models.CharField(max_length=255, verbose_name='Country Name')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('url', models.CharField(max_length=255, verbose_name='URL')),
                ('text', models.TextField(verbose_name='Text', blank=True)),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled')),
            ],
            options={
                'verbose_name': 'FOI Site',
                'verbose_name_plural': 'FOI Sites',
            },
        ),
    ]
