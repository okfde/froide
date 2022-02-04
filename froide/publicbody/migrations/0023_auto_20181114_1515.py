# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-14 14:15
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("georegion", "0004_georegion_description"),
        ("publicbody", "0022_auto_20180726_1151"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicbody",
            name="regions",
            field=models.ManyToManyField(blank=True, to="georegion.GeoRegion"),
        ),
        migrations.AlterField(
            model_name="publicbody",
            name="region",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="georegion.GeoRegion",
            ),
        ),
    ]
