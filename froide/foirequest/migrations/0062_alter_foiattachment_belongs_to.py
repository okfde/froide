# Generated by Django 4.1.4 on 2023-02-10 12:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("foirequest", "0061_foimessage_foirequest__email_m_304d80_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="foiattachment",
            name="belongs_to",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="foiattachment_set",
                to="foirequest.foimessage",
                verbose_name="Belongs to message",
            ),
        ),
    ]
