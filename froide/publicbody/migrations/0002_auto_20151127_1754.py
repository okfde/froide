# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('publicbody', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='jurisdiction',
            options={'ordering': ('rank', 'name'), 'verbose_name': 'Jurisdiction', 'verbose_name_plural': 'Jurisdictions'},
        ),
        migrations.AddField(
            model_name='publicbody',
            name='file_index',
            field=models.CharField(max_length=1024, blank=True),
        ),
        migrations.AddField(
            model_name='publicbody',
            name='org_chart',
            field=models.CharField(max_length=1024, blank=True),
        ),
    ]
