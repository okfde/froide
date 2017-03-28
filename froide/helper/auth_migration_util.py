from django.conf import settings


def get_app_model(db_name):
    a, m = db_name.split('_')
    return '%s.%s' % (a, m.title())


USER_DB_NAME = getattr(settings, 'CUSTOM_AUTH_USER_MODEL_DB', None) or 'account_user'
APP_MODEL = get_app_model(USER_DB_NAME)
APP_MODEL_NAME = APP_MODEL.lower()
