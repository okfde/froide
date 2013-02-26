# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'PublicBody.jurisdiction'
        db.alter_column('publicbody_publicbody', 'jurisdiction_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.Jurisdiction'], null=True, on_delete=models.SET_NULL))

        # Changing field 'PublicBody.site'
        db.alter_column('publicbody_publicbody', 'site_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True, on_delete=models.SET_NULL))

        # Changing field 'PublicBody.topic'
        db.alter_column('publicbody_publicbody', 'topic_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBodyTopic'], null=True, on_delete=models.SET_NULL))

        # Changing field 'PublicBody.parent'
        db.alter_column('publicbody_publicbody', 'parent_id', self.gf('django.db.models.fields.related.ForeignKey')(on_delete=models.SET_NULL, to=orm['publicbody.PublicBody'], null=True))

        # Changing field 'PublicBody._created_by'
        db.alter_column('publicbody_publicbody', '_created_by_id', self.gf('django.db.models.fields.related.ForeignKey')(on_delete=models.SET_NULL, to=orm['auth.User'], null=True))

        # Changing field 'PublicBody._updated_by'
        db.alter_column('publicbody_publicbody', '_updated_by_id', self.gf('django.db.models.fields.related.ForeignKey')(on_delete=models.SET_NULL, to=orm['auth.User'], null=True))

        # Changing field 'PublicBody.root'
        db.alter_column('publicbody_publicbody', 'root_id', self.gf('django.db.models.fields.related.ForeignKey')(on_delete=models.SET_NULL, to=orm['publicbody.PublicBody'], null=True))
        # Adding field 'PublicBodyTopic.rank'
        db.add_column('publicbody_publicbodytopic', 'rank',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


        # Changing field 'FoiLaw.jurisdiction'
        db.alter_column('publicbody_foilaw', 'jurisdiction_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.Jurisdiction'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiLaw.mediator'
        db.alter_column('publicbody_foilaw', 'mediator_id', self.gf('django.db.models.fields.related.ForeignKey')(on_delete=models.SET_NULL, to=orm['publicbody.PublicBody'], null=True))

        # Changing field 'FoiLaw.site'
        db.alter_column('publicbody_foilaw', 'site_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True, on_delete=models.SET_NULL))

    def backwards(self, orm):

        # Changing field 'PublicBody.jurisdiction'
        db.alter_column('publicbody_publicbody', 'jurisdiction_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.Jurisdiction'], null=True))

        # Changing field 'PublicBody.site'
        db.alter_column('publicbody_publicbody', 'site_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True))

        # Changing field 'PublicBody.topic'
        db.alter_column('publicbody_publicbody', 'topic_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBodyTopic'], null=True))

        # Changing field 'PublicBody.parent'
        db.alter_column('publicbody_publicbody', 'parent_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['publicbody.PublicBody']))

        # Changing field 'PublicBody._created_by'
        db.alter_column('publicbody_publicbody', '_created_by_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['auth.User']))

        # Changing field 'PublicBody._updated_by'
        db.alter_column('publicbody_publicbody', '_updated_by_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['auth.User']))

        # Changing field 'PublicBody.root'
        db.alter_column('publicbody_publicbody', 'root_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['publicbody.PublicBody']))
        # Deleting field 'PublicBodyTopic.rank'
        db.delete_column('publicbody_publicbodytopic', 'rank')


        # Changing field 'FoiLaw.jurisdiction'
        db.alter_column('publicbody_foilaw', 'jurisdiction_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.Jurisdiction'], null=True))

        # Changing field 'FoiLaw.mediator'
        db.alter_column('publicbody_foilaw', 'mediator_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['publicbody.PublicBody']))

        # Changing field 'FoiLaw.site'
        db.alter_column('publicbody_foilaw', 'site_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'publicbody.foilaw': {
            'Meta': {'object_name': 'FoiLaw'},
            'combined': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['publicbody.FoiLaw']", 'symmetrical': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jurisdiction': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.Jurisdiction']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'letter_end': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'letter_start': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'max_response_time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_response_time_unit': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'mediator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mediating_laws'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['publicbody.PublicBody']", 'blank': 'True', 'null': 'True'}),
            'meta': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'refusal_reasons': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'request_note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': "orm['sites.Site']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'publicbody.jurisdiction': {
            'Meta': {'object_name': 'Jurisdiction'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        'publicbody.publicbody': {
            'Meta': {'ordering': "('name',)", 'object_name': 'PublicBody'},
            '_created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'public_body_creators'", 'on_delete': 'models.SET_NULL', 'default': '1', 'to': "orm['auth.User']", 'blank': 'True', 'null': 'True'}),
            '_updated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'public_body_updaters'", 'on_delete': 'models.SET_NULL', 'default': '1', 'to': "orm['auth.User']", 'blank': 'True', 'null': 'True'}),
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classification': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'classification_slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'contact': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'depth': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jurisdiction': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.Jurisdiction']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'laws': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['publicbody.FoiLaw']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'number_of_requests': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'other_names': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['publicbody.PublicBody']", 'blank': 'True', 'null': 'True'}),
            'request_note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'descendants'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['publicbody.PublicBody']", 'blank': 'True', 'null': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': "orm['sites.Site']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.PublicBodyTopic']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'website_dump': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'publicbody.publicbodytopic': {
            'Meta': {'object_name': 'PublicBodyTopic'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['publicbody']