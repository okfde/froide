# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'FoiRequest.jurisdiction'
        db.alter_column('foirequest_foirequest', 'jurisdiction_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.Jurisdiction'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiRequest.same_as'
        db.alter_column('foirequest_foirequest', 'same_as_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['foirequest.FoiRequest'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiRequest.site'
        db.alter_column('foirequest_foirequest', 'site_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiRequest.public_body'
        db.alter_column('foirequest_foirequest', 'public_body_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBody'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiRequest.user'
        db.alter_column('foirequest_foirequest', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiRequest.law'
        db.alter_column('foirequest_foirequest', 'law_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.FoiLaw'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiEvent.public_body'
        db.alter_column('foirequest_foievent', 'public_body_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBody'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiEvent.user'
        db.alter_column('foirequest_foievent', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiAttachment.redacted'
        db.alter_column('foirequest_foiattachment', 'redacted_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['foirequest.FoiAttachment'], null=True, on_delete=models.SET_NULL))
        # Adding field 'FoiMessage.content_hidden'
        db.add_column('foirequest_foimessage', 'content_hidden',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


        # Changing field 'FoiMessage.sender_public_body'
        db.alter_column('foirequest_foimessage', 'sender_public_body_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, on_delete=models.SET_NULL, to=orm['publicbody.PublicBody']))

        # Changing field 'FoiMessage.sender_user'
        db.alter_column('foirequest_foimessage', 'sender_user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, on_delete=models.SET_NULL))

        # Changing field 'FoiMessage.recipient_public_body'
        db.alter_column('foirequest_foimessage', 'recipient_public_body_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, on_delete=models.SET_NULL, to=orm['publicbody.PublicBody']))

        # Changing field 'PublicBodySuggestion.user'
        db.alter_column('foirequest_publicbodysuggestion', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, on_delete=models.SET_NULL))

    def backwards(self, orm):

        # Changing field 'FoiRequest.jurisdiction'
        db.alter_column('foirequest_foirequest', 'jurisdiction_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.Jurisdiction'], null=True))

        # Changing field 'FoiRequest.same_as'
        db.alter_column('foirequest_foirequest', 'same_as_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['foirequest.FoiRequest'], null=True))

        # Changing field 'FoiRequest.site'
        db.alter_column('foirequest_foirequest', 'site_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True))

        # Changing field 'FoiRequest.public_body'
        db.alter_column('foirequest_foirequest', 'public_body_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBody'], null=True))

        # Changing field 'FoiRequest.user'
        db.alter_column('foirequest_foirequest', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True))

        # Changing field 'FoiRequest.law'
        db.alter_column('foirequest_foirequest', 'law_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.FoiLaw'], null=True))

        # Changing field 'FoiEvent.public_body'
        db.alter_column('foirequest_foievent', 'public_body_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBody'], null=True))

        # Changing field 'FoiEvent.user'
        db.alter_column('foirequest_foievent', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True))

        # Changing field 'FoiAttachment.redacted'
        db.alter_column('foirequest_foiattachment', 'redacted_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['foirequest.FoiAttachment'], null=True))
        # Deleting field 'FoiMessage.content_hidden'
        db.delete_column('foirequest_foimessage', 'content_hidden')


        # Changing field 'FoiMessage.sender_public_body'
        db.alter_column('foirequest_foimessage', 'sender_public_body_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['publicbody.PublicBody']))

        # Changing field 'FoiMessage.sender_user'
        db.alter_column('foirequest_foimessage', 'sender_user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True))

        # Changing field 'FoiMessage.recipient_public_body'
        db.alter_column('foirequest_foimessage', 'recipient_public_body_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['publicbody.PublicBody']))

        # Changing field 'PublicBodySuggestion.user'
        db.alter_column('foirequest_publicbodysuggestion', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True))

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
        'foirequest.foiattachment': {
            'Meta': {'ordering': "('name',)", 'object_name': 'FoiAttachment'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'belongs_to': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiMessage']", 'null': 'True'}),
            'can_approve': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'filetype': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'format': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_redacted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'redacted': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiAttachment']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'foirequest.foievent': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'FoiEvent'},
            'context_json': ('django.db.models.fields.TextField', [], {}),
            'event_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'public_body': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.PublicBody']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiRequest']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        },
        'foirequest.foimessage': {
            'Meta': {'ordering': "('timestamp',)", 'object_name': 'FoiMessage'},
            'content_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_escalation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_postal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_response': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'not_publishable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'original': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'plaintext': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'recipient': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'recipient_email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'recipient_public_body': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'received_messages'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['publicbody.PublicBody']"}),
            'redacted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiRequest']"}),
            'sender_email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'sender_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'sender_public_body': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'send_messages'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['publicbody.PublicBody']"}),
            'sender_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'sent': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'})
        },
        'foirequest.foirequest': {
            'Meta': {'ordering': "('last_message',)", 'object_name': 'FoiRequest'},
            'checked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'costs': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'due_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'first_message': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_foi': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'jurisdiction': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.Jurisdiction']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'last_message': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'law': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.FoiLaw']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'public_body': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.PublicBody']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'refusal_reason': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'resolution': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'resolved_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'same_as': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiRequest']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'same_as_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'secret_address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'visibility': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        },
        'foirequest.publicbodysuggestion': {
            'Meta': {'ordering': "('timestamp',)", 'object_name': 'PublicBodySuggestion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public_body': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.PublicBody']"}),
            'reason': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiRequest']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL'})
        },
        'foirequest.taggedfoirequest': {
            'Meta': {'object_name': 'TaggedFoiRequest'},
            'content_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiRequest']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'foirequest_taggedfoirequest_items'", 'to': "orm['taggit.Tag']"})
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
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        }
    }

    complete_apps = ['foirequest']