# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('foirequest', '0004_foirequest_is_blocked'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='foirequest',
            options={'ordering': ('-last_message',), 'get_latest_by': 'last_message', 'verbose_name': 'Freedom of Information Request', 'verbose_name_plural': 'Freedom of Information Requests', 'permissions': (('see_private', 'Can see private requests'),)},
        ),
    ]
