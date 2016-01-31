# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0003_auto_20160125_2127'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_trusted',
            field=models.BooleanField(default=False, verbose_name='Trusted'),
        ),
    ]
