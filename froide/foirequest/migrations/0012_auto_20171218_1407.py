# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-12-18 13:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("foirequest", "0011_deliverystatus"),
    ]

    operations = [
        migrations.AlterField(
            model_name="foimessage",
            name="email_message_id",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
    ]
