# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    depends_on = (
        # be aggressive in asserting the dep
        # (dep is probably weaker than this i.e. lower number from publicbody
        # and higher from foirequest ...)
        ('publicbody', '0020_auto__chg_field_publicbody_jurisdiction__chg_field_publicbody_site__ch.py'),
    )

    def forwards(self, orm):
        
        # Adding model 'FoiRequest'
        db.create_table('foirequest_foirequest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=255, db_index=True)),
            ('resolution', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('public_body', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBody'], null=True, blank=True)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('visibility', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('first_message', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_message', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('resolved_on', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('due_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('secret_address', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, db_index=True)),
            ('secret', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('law', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.FoiLaw'], null=True, blank=True)),
            ('costs', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('refusal_reason', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True)),
        ))
        db.send_create_signal('foirequest', ['FoiRequest'])

        # Adding model 'PublicBodySuggestion'
        db.create_table('foirequest_publicbodysuggestion', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('request', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['foirequest.FoiRequest'])),
            ('public_body', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBody'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('foirequest', ['PublicBodySuggestion'])

        # Adding model 'FoiMessage'
        db.create_table('foirequest_foimessage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('request', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['foirequest.FoiRequest'])),
            ('sent', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_response', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('sender_user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('sender_email', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('sender_name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('sender_public_body', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBody'], null=True, blank=True)),
            ('recipient', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(blank=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('plaintext', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('html', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('original', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('redacted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('_status', self.gf('django.db.models.fields.SmallIntegerField')(default=None, null=True, blank=True)),
            ('_resolution', self.gf('django.db.models.fields.SmallIntegerField')(default=None, null=True, blank=True)),
            ('_visibility', self.gf('django.db.models.fields.SmallIntegerField')(default=1)),
        ))
        db.send_create_signal('foirequest', ['FoiMessage'])

        # Adding model 'FoiAttachment'
        db.create_table('foirequest_foiattachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('belongs_to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['foirequest.FoiMessage'], null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('size', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('filetype', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('format', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('foirequest', ['FoiAttachment'])

        # Adding model 'FoiEvent'
        db.create_table('foirequest_foievent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('request', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['foirequest.FoiRequest'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('public_body', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['publicbody.PublicBody'], null=True, blank=True)),
            ('event_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('context_json', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('foirequest', ['FoiEvent'])


    def backwards(self, orm):
        
        # Deleting model 'FoiRequest'
        db.delete_table('foirequest_foirequest')

        # Deleting model 'PublicBodySuggestion'
        db.delete_table('foirequest_publicbodysuggestion')

        # Deleting model 'FoiMessage'
        db.delete_table('foirequest_foimessage')

        # Deleting model 'FoiAttachment'
        db.delete_table('foirequest_foiattachment')

        # Deleting model 'FoiEvent'
        db.delete_table('foirequest_foievent')


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
            'belongs_to': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiMessage']", 'null': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'filetype': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'format': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'foirequest.foievent': {
            'Meta': {'ordering': "('timestamp',)", 'object_name': 'FoiEvent'},
            'context_json': ('django.db.models.fields.TextField', [], {}),
            'event_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public_body': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.PublicBody']", 'null': 'True', 'blank': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiRequest']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'foirequest.foimessage': {
            'Meta': {'ordering': "('timestamp',)", 'object_name': 'FoiMessage'},
            '_resolution': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            '_status': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            '_visibility': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_response': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'original': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'plaintext': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'recipient': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'redacted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiRequest']"}),
            'sender_email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'sender_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'sender_public_body': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.PublicBody']", 'null': 'True', 'blank': 'True'}),
            'sender_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'sent': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'})
        },
        'foirequest.foirequest': {
            'Meta': {'ordering': "('last_message',)", 'object_name': 'FoiRequest'},
            'costs': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'due_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'first_message': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_message': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'law': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.FoiLaw']", 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'public_body': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.PublicBody']", 'null': 'True', 'blank': 'True'}),
            'refusal_reason': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'resolution': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'resolved_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'secret_address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']", 'null': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'visibility': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        },
        'foirequest.publicbodysuggestion': {
            'Meta': {'ordering': "('timestamp',)", 'object_name': 'PublicBodySuggestion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public_body': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['publicbody.PublicBody']"}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['foirequest.FoiRequest']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'publicbody.foilaw': {
            'Meta': {'object_name': 'FoiLaw'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jurisdiction': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'letter_end': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'letter_start': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'max_response_time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_response_time_unit': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '3'}),
            'refusal_reasons': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': "orm['sites.Site']", 'null': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'})
        },
        'publicbody.publicbody': {
            'Meta': {'object_name': 'PublicBody'},
            '_created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'public_body_creators'", 'null': 'True', 'to': "orm['auth.User']"}),
            '_updated_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'public_body_updaters'", 'null': 'True', 'to': "orm['auth.User']"}),
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classification': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'classification_slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'contact': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'depth': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'geography': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'laws': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['publicbody.FoiLaw']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'number_of_requests': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'children'", 'null': 'True', 'blank': 'True', 'to': "orm['publicbody.PublicBody']"}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'descendants'", 'null': 'True', 'blank': 'True', 'to': "orm['publicbody.PublicBody']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': "orm['sites.Site']", 'null': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'topic': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'topic_slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'website_dump': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['foirequest']
