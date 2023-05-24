# Generated by Django 3.2.8 on 2022-02-15 16:38

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import froide.helper.storage
import froide.organization.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("website", models.URLField(blank=True)),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("description", models.TextField(blank=True)),
                ("email_domain", models.CharField(blank=True, max_length=255)),
                (
                    "logo",
                    models.ImageField(
                        blank=True,
                        null=True,
                        storage=froide.helper.storage.HashedFilenameStorage(),
                        upload_to=froide.organization.models.logo_path,
                    ),
                ),
            ],
            options={
                "verbose_name": "organization",
                "verbose_name_plural": "organizations",
            },
        ),
        migrations.CreateModel(
            name="OrganizationMembership",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("email", models.CharField(blank=True, max_length=255)),
                (
                    "role",
                    models.CharField(
                        choices=[("owner", "owner"), ("member", "member")],
                        max_length=30,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("inactive", "inactive"),
                            ("invited", "invited"),
                            ("active", "active"),
                        ],
                        max_length=30,
                    ),
                ),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="organization.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="organization",
            name="members",
            field=models.ManyToManyField(
                through="organization.OrganizationMembership",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(
                condition=models.Q(("user__isnull", False)),
                fields=("user", "organization"),
                name="unique_user_organization",
            ),
        ),
    ]
