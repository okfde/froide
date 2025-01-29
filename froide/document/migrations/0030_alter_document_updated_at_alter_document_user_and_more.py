# Generated by Django 4.2.16 on 2025-01-29 15:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("filingcabinet", "0030_alter_collectiondirectory_id_and_more"),
        ("document", "0029_documentcollection_foirequests"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name="document",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(app_label)s_%(class)s",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
        migrations.AlterField(
            model_name="documentcollection",
            name="documents",
            field=models.ManyToManyField(
                blank=True,
                related_name="%(app_label)s_%(class)s",
                through="filingcabinet.CollectionDocument",
                to=settings.FILINGCABINET_DOCUMENT_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="documentcollection",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(app_label)s_%(class)s",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
    ]
