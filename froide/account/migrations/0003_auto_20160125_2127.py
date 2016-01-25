# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_auto_20150729_0828'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='date_left',
            field=models.DateTimeField(default=None, null=True, verbose_name='date left', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_deleted',
            field=models.BooleanField(default=False, help_text='Designates whether this user was deleted.', verbose_name='deleted'),
        ),
    ]
