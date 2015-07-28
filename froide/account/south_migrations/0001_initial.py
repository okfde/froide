# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from froide.helper.auth_migration_util import USER_DB_NAME, APP_MODEL, APP_MODEL_NAME


class Migration(SchemaMigration):

    def forwards(self, orm):
        if USER_DB_NAME == 'account_user':
            db.create_table('account_user', (
                ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
                ('date_joined', self.gf('django.db.models.fields.DateTimeField')(**{})),
                ('email', self.gf('django.db.models.fields.EmailField')(**{'max_length': '75', 'blank': 'True'})),
                ('first_name', self.gf('django.db.models.fields.CharField')(**{'max_length': '30', 'blank': 'True'})),
                ('groups', self.gf('django.db.models.fields.related.ManyToManyField')(**{'symmetrical': 'False', 'related_name': 'user_set', 'blank': 'True', 'to': orm['auth.Group']})),
                ('is_active', self.gf('django.db.models.fields.BooleanField')(**{'default': 'True'})),
                ('is_staff', self.gf('django.db.models.fields.BooleanField')(**{'default': 'False'})),
                ('is_superuser', self.gf('django.db.models.fields.BooleanField')(**{'default': 'False'})),
                ('last_login', self.gf('django.db.models.fields.DateTimeField')(**{})),
                ('last_name', self.gf('django.db.models.fields.CharField')(**{'max_length': '30', 'blank': 'True'})),
                ('password', self.gf('django.db.models.fields.CharField')(**{'max_length': '128'})),
                ('user_permissions', self.gf('django.db.models.fields.related.ManyToManyField')(**{'symmetrical': 'False', 'related_name': 'user_set', 'blank': 'True', 'to': orm['auth.Permission']})),
                ('username', self.gf('django.db.models.fields.CharField')(**{'unique': 'True', 'max_length': '30'}))
            ))
            db.send_create_signal('account', ['User'])

        # Adding M2M table for field groups on 'User'
        m2m_table_name = db.shorten_name(u'account_user_groups')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'account.user'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'User'
        m2m_table_name = db.shorten_name(u'account_user_user_permissions')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'account.user'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'permission_id'])

        # Adding model 'Profile'
        db.create_table('account_profile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm[APP_MODEL], unique=True)),
        ))
        db.send_create_signal('account', ['Profile'])

    def backwards(self, orm):
        # Deleting model 'Profile'
        db.delete_table('account_profile')

        if USER_DB_NAME == 'account_user':
            # Deleting model 'User'
            db.delete_table('account_user')

    models = {
        'account.profile': {
            'Meta': {'object_name': 'Profile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['%s']" % APP_MODEL, 'unique': 'True'})
        },
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
        APP_MODEL_NAME: {
            'Meta': {'object_name': 'User', 'db_table': "'%s'" % USER_DB_NAME},
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
        }
    }

    complete_apps = ['account']
