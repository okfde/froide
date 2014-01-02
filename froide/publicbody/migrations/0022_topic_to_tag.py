# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for publicbody in orm.PublicBody._default_manager.select_related('topic').all():
            if publicbody.topic:
                tag, exist = orm.PublicBodyTag.objects.get_or_create(
                        name=publicbody.topic.name,
                        slug=publicbody.topic.slug,
                        rank=publicbody.topic.rank,
                        is_topic=True
                )
                orm.TaggedPublicBody.objects.create(
                    content_object=publicbody,
                    tag=tag
                )

    def backwards(self, orm):
        "Write your backwards methods here."
        for publicbody in orm.PublicBody._default_manager.select_related('topic').all():
            tags = publicbody.tags.filter(is_topic=True)
            if tags:
                orm.PublicBodyTopic.objects.create(
                    publicbody=publicbody,
                    name=tags[0].name,
                    slug=tags[0].slug
                )

    models = {
        u'account.user': {
            'Meta': {'object_name': 'User'},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'organization': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'organization_url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'publicbody.foilaw': {
            'Meta': {'object_name': 'FoiLaw'},
            'combined': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['publicbody.FoiLaw']", 'symmetrical': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jurisdiction': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['publicbody.Jurisdiction']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'letter_end': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'letter_start': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'max_response_time': ('django.db.models.fields.IntegerField', [], {'default': '30', 'null': 'True', 'blank': 'True'}),
            'max_response_time_unit': ('django.db.models.fields.CharField', [], {'default': "'day'", 'max_length': '32', 'blank': 'True'}),
            'mediator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mediating_laws'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': u"orm['publicbody.PublicBody']", 'blank': 'True', 'null': 'True'}),
            'meta': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'refusal_reasons': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'request_note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['sites.Site']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'publicbody.jurisdiction': {
            'Meta': {'object_name': 'Jurisdiction'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'publicbody.publicbody': {
            'Meta': {'ordering': "('name',)", 'object_name': 'PublicBody'},
            '_created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'public_body_creators'", 'on_delete': 'models.SET_NULL', 'default': '1', 'to': u"orm['account.User']", 'blank': 'True', 'null': 'True'}),
            '_updated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'public_body_updaters'", 'on_delete': 'models.SET_NULL', 'default': '1', 'to': u"orm['account.User']", 'blank': 'True', 'null': 'True'}),
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classification': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'classification_slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'contact': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'depth': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jurisdiction': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['publicbody.Jurisdiction']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'laws': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['publicbody.FoiLaw']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'number_of_requests': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'other_names': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': u"orm['publicbody.PublicBody']", 'blank': 'True', 'null': 'True'}),
            'request_note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'descendants'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': u"orm['publicbody.PublicBody']", 'blank': 'True', 'null': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['sites.Site']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['publicbody.PublicBodyTopic']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'website_dump': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'publicbody.publicbodytag': {
            'Meta': {'object_name': 'PublicBodyTag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_topic': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
        },
        u'publicbody.publicbodytopic': {
            'Meta': {'object_name': 'PublicBodyTopic'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'publicbody.taggedpublicbody': {
            'Meta': {'object_name': 'TaggedPublicBody'},
            'content_object': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['publicbody.PublicBody']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'publicbody_taggedpublicbody_items'", 'to': u"orm['publicbody.PublicBodyTag']"})
        },
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['publicbody']
    symmetrical = True
