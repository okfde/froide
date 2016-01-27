# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('foirequest', '0002_auto_20150728_1829'),
    ]

    operations = [
        migrations.AddField(
            model_name='foirequest',
            name='reference',
            field=models.CharField(max_length=255, verbose_name='Reference', blank=True),
        ),
    ]
