# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('publicbody', '0002_auto_20151127_1754'),
    ]

    operations = [
        migrations.AlterField(
            model_name='publicbody',
            name='file_index',
            field=models.CharField(max_length=1024, verbose_name='file index', blank=True),
        ),
        migrations.AlterField(
            model_name='publicbody',
            name='org_chart',
            field=models.CharField(max_length=1024, verbose_name='organisational chart', blank=True),
        ),
    ]
