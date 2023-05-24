# Generated by Django 2.1.7 on 2019-03-25 19:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("georegion", "0008_auto_20190325_1956"),
    ]

    operations = [
        migrations.AlterField(
            model_name="georegion",
            name="depth",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="georegion",
            name="path",
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
