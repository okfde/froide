# Generated by Django 4.2.4 on 2024-05-06 12:32

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("publicbody", "0046_foilawtranslation_overdue_reply"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="classification",
            options={
                "verbose_name": "Classification",
                "verbose_name_plural": "Classifications",
            },
        ),
    ]
