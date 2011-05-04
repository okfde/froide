# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FoiLaw'
        db.create_table('publicbody_foilaw', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('letter_start', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('letter_end', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('jurisdiction', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=3)),
            ('max_response_time', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('max_response_time_unit', self.gf('django.db.models.fields.CharField')(max_length=32, blank=True)),
            ('refusal_reasons', self.gf('django.db.models.fields.TextField')()),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['sites.Site'], null=True)),
        ))
        db.send_create_signal('publicbody', ['FoiLaw'])

        # Adding model 'PublicBody'
        db.create_table('publicbody_publicbody', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('topic', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('topic_slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='children', null=True, blank=True, to=orm['publicbody.PublicBody'])),
            ('root', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='descendants', null=True, blank=True, to=orm['publicbody.PublicBody'])),
            ('depth', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('classification', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('classification_slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('contact', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('address', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('website_dump', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('_created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='public_body_creators', null=True, to=orm['auth.User'])),
            ('_updated_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='public_body_updaters', null=True, to=orm['auth.User'])),
            ('confirmed', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('number_of_requests', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['sites.Site'], null=True)),
            ('geography', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('publicbody', ['PublicBody'])

        # Adding M2M table for field laws on 'PublicBody'
        db.create_table('publicbody_publicbody_laws', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('publicbody', models.ForeignKey(orm['publicbody.publicbody'], null=False)),
            ('foilaw', models.ForeignKey(orm['publicbody.foilaw'], null=False))
        ))
        db.create_unique('publicbody_publicbody_laws', ['publicbody_id', 'foilaw_id'])


    def backwards(self, orm):
        
        # Deleting model 'FoiLaw'
        db.delete_table('publicbody_foilaw')

        # Deleting model 'PublicBody'
        db.delete_table('publicbody_publicbody')

        # Removing M2M table for field laws on 'PublicBody'
        db.delete_table('publicbody_publicbody_laws')


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

    complete_apps = ['publicbody']
