# Generated by Django 3.2.14 on 2022-09-01 16:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("publicbody", "0039_publicbody_alternative_emails"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="foilaw",
            options={
                "ordering": ("-meta", "-priority"),
                "verbose_name": "Freedom of Information Law",
                "verbose_name_plural": "Freedom of Information Laws",
            },
        ),
    ]