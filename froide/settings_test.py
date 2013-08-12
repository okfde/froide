# -*- coding: utf-8 -*-
# Django settings for froide project.

from .settings import *  # noqa

DEBUG = False

TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'froide': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


def fake_convert_pdf(infile, outpath):
    _, filename = os.path.split(infile)
    name, ext = filename.rsplit('.', 1)
    output = os.path.join(outpath, '%s.pdf' % name)
    args = ['cp', infile, output]
    return args, output

FROIDE_CONFIG.update(dict(
    doc_conversion_call_func=fake_convert_pdf,
    default_law=10000
))

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

CACHES = {
    'default': {
        # 'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

TEST_RUNNER = 'discover_runner.DiscoverRunner'

# 'chrome' or 'firefox' or 'phantomjs'
TEST_SELENIUM_DRIVER = 'phantomjs'

SOUTH_TESTS_MIGRATE = False

USE_X_ACCEL_REDIRECT = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = 'info@example.com'

# Default test domain
FOI_EMAIL_DOMAIN = 'fragdenstaat.de'

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'froide',
    },
}

HAYSTACK_SIGNAL_PROCESSOR = 'celery_haystack.signals.CelerySignalProcessor'

CELERY_RESULT_BACKEND = "database"
CELERY_RESULT_DBURI = "sqlite:///dev.db"

CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_ALWAYS_EAGER = True
