# Generated by Django 4.0.8 on 2022-12-19 13:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("foirequest", "0060_foirequest_banner"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="foimessage",
            index=models.Index(
                fields=["email_message_id"], name="foirequest__email_m_304d80_idx"
            ),
        ),
    ]
