# Generated by Django 3.1.4 on 2021-02-03 11:37

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("foirequest", "0048_auto_20201221_1953"),
    ]

    operations = [
        migrations.AddField(
            model_name="foiproject",
            name="language",
            field=models.CharField(
                blank=True,
                choices=settings.LANGUAGES,
                default=settings.LANGUAGE_CODE,
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="foirequest",
            name="language",
            field=models.CharField(
                blank=True,
                choices=settings.LANGUAGES,
                default=settings.LANGUAGE_CODE,
                max_length=10,
            ),
        ),
    ]
