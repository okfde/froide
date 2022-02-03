# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-08-07 13:20
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("foirequest", "0027_auto_20180726_1759"),
    ]

    operations = [
        migrations.AlterField(
            model_name="foiattachment",
            name="document",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="attachment",
                to=settings.FILINGCABINET_DOCUMENT_MODEL,
            ),
        ),
    ]
