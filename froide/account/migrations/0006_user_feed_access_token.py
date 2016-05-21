# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0005_user_is_blocked'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='feed_access_token',
            field=models.CharField(default=b'8064c2832404416dbedbc11036fa8254', max_length=40, verbose_name='feed access key', blank=True),
        ),
    ]
