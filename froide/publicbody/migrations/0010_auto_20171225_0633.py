# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-12-25 05:33
from __future__ import unicode_literals

from django.db import migrations


def create_categories(apps, schema_editor):
    """
    Copy all PublicBodyTags to Categories
    """
    TaggedPublicBody = apps.get_model("publicbody", "TaggedPublicBody")
    Category = apps.get_model("publicbody", "Category")

    categories = {}
    for tpb in TaggedPublicBody.objects.all():
        if tpb.tag.slug in categories:
            category = categories[tpb.tag.slug]
        else:
            category = Category.add_root(
                name=tpb.tag.name, slug=tpb.tag.slug, is_topic=tpb.tag.is_topic
            )
            categories[tpb.tag.slug] = category
        pb = tpb.content_object
        pb.categories.add(category)


class Migration(migrations.Migration):
    dependencies = [
        ("publicbody", "0009_auto_20171225_0631"),
    ]

    operations = [
        migrations.RunPython(create_categories),
    ]
