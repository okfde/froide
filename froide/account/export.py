from datetime import timedelta
import json
import os
import tempfile
import zipfile

from django.core.files.storage import default_storage
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.urls import reverse

from crossdomainmedia import CrossDomainMediaAuth

from froide.helper.api_utils import get_dict

from .utils import send_mail_user
from .tasks import start_export_task

PURPOSE = 'dataexport'
EXPORT_MEDIA_PREFIX = 'export'
EXPORT_MAX_AGE = timedelta(days=7)
EXPORT_LIMIT = timedelta(hours=6)


def get_path(token):
    return os.path.join(EXPORT_MEDIA_PREFIX, '{}.zip'.format(token))


class ExportRegistry:
    def __init__(self):
        self.callbacks = []

    def register(self, func):
        self.callbacks.append(func)

    def get_export_files(self, user):
        for callback in self.callbacks:
            yield from callback(user)


def request_export(user):
    from froide.accesstoken.models import AccessToken

    access_token = AccessToken.objects.get_by_user(user, purpose=PURPOSE)
    if access_token is not None:
        age = timezone.now() - access_token.timestamp
        if age < EXPORT_LIMIT:
            return access_token.timestamp + EXPORT_LIMIT

        path = get_path(access_token.token)
        if not default_storage.exists(path):
            return True

    start_export_task.delay(user.id)
    return None


def get_export_access_token_by_token(token_uuid):
    from froide.accesstoken.models import AccessToken

    return AccessToken.objects.get_by_token(token_uuid, purpose=PURPOSE)


def get_export_access_token(user, access_token=None):
    from froide.accesstoken.models import AccessToken

    if access_token is None:
        access_token = AccessToken.objects.get_by_user(user, purpose=PURPOSE)
        if access_token is None:
            return None

    age = timezone.now() - access_token.timestamp
    if age > EXPORT_MAX_AGE:
        delete_export(access_token.token)
        return None

    path = get_path(access_token.token)
    if not default_storage.exists(path):
        return False

    return access_token


def delete_export(token):
    path = get_path(token)
    if default_storage.exists(path):
        default_storage.delete(path)


def delete_all_expired_exports():
    from froide.accesstoken.models import AccessToken

    old_export_date = timezone.now() - EXPORT_MAX_AGE
    access_tokens = AccessToken.objects.filter(
        purpose=PURPOSE,
        timestamp__lte=old_export_date
    )
    for at in access_tokens:
        delete_export(at.token)

    access_tokens.delete()


def create_export(user, notification_user=None):
    from froide.accesstoken.models import AccessToken

    if notification_user is not None and notification_user != user:
        if not notification_user.is_superuser:
            raise Exception('Can only export user as super user')

    access_token, created = AccessToken.objects.get_or_create(
        user=user, purpose=PURPOSE
    )
    token = access_token.token
    if not created:
        delete_export(token)
        token = AccessToken.objects.reset(user, purpose=PURPOSE)

    export_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        zfile = zipfile.ZipFile(export_file, 'w')
        for path, filebytes in registry.get_export_files(user):
            zfile.writestr(os.path.join('export', path), filebytes)
    except Exception:
        zfile.close()
        export_file.close()
        os.remove(export_file.name)
        raise
    finally:
        try:
            zfile.close()
        except ValueError:
            pass

    export_file.flush()
    export_file.seek(0)

    path = get_path(token)
    default_storage.save(path, export_file)

    export_file.close()
    os.remove(export_file.name)

    if notification_user is None or notification_user == user:
        email_template = 'account/emails/export_ready.txt'
        notification_url = settings.SITE_URL + reverse('account-download_export')
        notification_user = user
    else:
        email_template = 'account/emails/export_ready_admin.txt'
        notification_url = ''

    body = render_to_string(email_template, {
        'url': notification_url,
        'name': user.get_full_name(),
        'days': EXPORT_MAX_AGE.days,
        'site_name': settings.SITE_NAME
    })
    send_mail_user(_('Your data export is ready'), body, notification_user)


registry = ExportRegistry()


@registry.register
def export_user_data(user):
    from .models import Application

    user_data = get_dict(user, (
        "id", "first_name", "last_name", "email",
        "address", "terms",
        "organization", "organization_url", "private",
        "date_joined", "is_staff",
        'profile_text', (
            'profile_photo',
            lambda x: os.path.basename(x.path) if x else None
        ),
        (
            'tags', lambda x: ','.join(str(t) for t in x.all())
        ),
        'is_trusted', 'is_blocked',
        'date_deactivated', 'is_active', 'is_staff',
    ))
    yield (
        'account.json', json.dumps(user_data).encode('utf-8')
    )
    if user.profile_photo:
        filename = os.path.basename(user.profile_photo.path)
        with open(user.profile_photo.path, 'rb') as f:
            yield (filename, f.read())

    apps = Application.objects.filter(user=user)
    if apps:
        fields = (
            'id',
            'client_id',
            'redirect_uris',
            'client_type',
            'authorization_grant_type',
            'client_secret',
            'name',
            'skip_authorization',
            'created',
            'updated',
            'description',
            'homepage',
            'image_url',
            'auto_approve_scopes',
        )
        yield (
            'apps.json',
            json.dumps([
                get_dict(a, fields) for a in apps
            ]).encode('utf-8')
        )
    grants = (
        user.oauth2_provider_grant.all()
        .select_related('application')
    )
    accesstokens = (
        user.oauth2_provider_accesstoken.all()
        .select_related('application')
    )
    refreshtokens = (
        user.oauth2_provider_refreshtoken.all()
        .select_related('application')
    )
    yield (
        'oauth.json',
        json.dumps({
            'grants': [
                get_dict(g, (
                    'id',
                    'code', 'application_id',
                    'application__name',
                    'application__description',
                    'expires',
                    'redirect_uri', 'scope',
                    'created',
                    'updated',
                )) for g in grants
            ],
            'accesstokens': [
                get_dict(a, (
                    'id',
                    'source_refresh_token_id',
                    'token',
                    'application_id',
                    'application__name',
                    'application__description',
                    'expires',
                    'scope',
                    'created',
                    'updated',
                )) for a in accesstokens
            ],
            'refreshtokens': [
                get_dict(a, (
                    'id', 'token',
                    'application_id',
                    'application__name',
                    'application__description',
                    'access_token_id',
                    'created',
                    'updated',
                    'revoked',
                )) for a in refreshtokens
            ],
        }).encode('utf-8')
    )


class ExportCrossDomainMediaAuth(CrossDomainMediaAuth):
    '''
    Create your own custom CrossDomainMediaAuth class
    and implement at least these methods
    '''
    TOKEN_MAX_AGE_SECONDS = 60
    SITE_URL = settings.SITE_URL
    DEBUG = False

    def is_media_public(self):
        '''
        Always False
        '''
        return False

    def has_perm(self, request):
        ctx = self.context
        obj = ctx['object']
        return obj.user == request.user

    def get_auth_url(self):
        '''
        Give URL path to authenticating view
        for the media described in context
        '''
        obj = self.context['object']
        return reverse('account-download_export_token', kwargs={
            'token': obj.token
        })

    def get_media_file_path(self):
        '''
        Return the URL path relative to MEDIA_ROOT for debug mode
        '''
        obj = self.context['object']
        return get_path(obj.token)
