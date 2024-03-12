# Generated by Django 4.0.7 on 2022-10-06 18:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publicbody", "0041_auto_20221006_1934"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="publicbody",
            name="change_proposals",
        ),
        migrations.AlterField(
            model_name="publicbodychangeproposal",
            name="publicbody",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="change_proposals",
                to="publicbody.publicbody",
            ),
        ),
    ]
