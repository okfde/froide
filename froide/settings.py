# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
import sys
import re

from celery.schedules import crontab

from configurations import Configuration, importer, values
importer.install(check_options=True)

from django.utils.translation import ugettext_lazy as _


def rec(x):
    return re.compile(x, re.I | re.U)


# Django settings for froide project.


class Base(Configuration):
    DEBUG = values.BooleanValue(True)

    DATABASES = values.DatabaseURLValue('spatialite:///dev.db')
    SPATIALITE_LIBRARY_PATH = '/usr/local/lib/mod_spatialite.dylib'
    CONN_MAX_AGE = None

    INSTALLED_APPS = values.ListValue([
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.admin',
        'django_comments',
        'django.contrib.flatpages',
        'django.contrib.sitemaps',
        'django.contrib.humanize',
        'django.contrib.gis',

        # external
        'haystack',
        'taggit',
        'overextends',
        'storages',
        'treebeard',
        'django_filters',

        # Semi-external
        'filingcabinet',

        # local
        'froide.foirequest',
        'froide.foirequestfollower',
        'froide.frontpage',
        'froide.georegion',
        'froide.publicbody',
        'froide.document',
        'froide.account',
        'froide.team',
        'froide.foisite',
        'froide.helper',

        # API
        'oauth2_provider',
        'rest_framework',
    ])

    CACHES = values.CacheURLValue('dummy://')

    # ############# Site Configuration #########

    # Make this unique, and don't share it with anybody.
    SECRET_KEY = 'make_me_unique!!'

    SITE_NAME = values.Value('Froide')
    SITE_EMAIL = values.Value('info@froide.example.com')
    SITE_URL = values.Value('http://localhost:8000')

    SITE_ID = values.IntegerValue(1)

    ADMINS = (
        # ('Your Name', 'your_email@example.com'),
    )

    MANAGERS = ADMINS

    INTERNAL_IPS = values.TupleValue(('127.0.0.1',))

    # ############## PATHS ###############

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    LOCALE_PATHS = values.TupleValue(
        (os.path.abspath(os.path.join(PROJECT_ROOT, '..', "locale")),)
    )

    GEOIP_PATH = None

    # Absolute filesystem path to the directory that will hold user-uploaded files.
    # Example: "/home/media/media.lawrence.com/media/"
    MEDIA_ROOT = values.Value(os.path.abspath(os.path.join(PROJECT_ROOT,
                                                           "..", "files")))

    # URL that handles the media served from MEDIA_ROOT. Make sure to use a
    # trailing slash.
    # Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
    MEDIA_URL = values.Value('/files/')

    # Sub path in MEDIA_ROOT that will hold FOI attachments
    FOI_MEDIA_PATH = values.Value('foi')
    FOI_MEDIA_URL = values.Value('/files/')
    FOI_MEDIA_DOMAIN = values.Value('')
    FOI_MEDIA_TOKENS = False
    FOI_MEDIA_TOKEN_EXPIRY = 2 * 60

    # Absolute path to the directory static files should be collected to.
    # Don't put anything in this directory yourself; store your static files
    # in apps' "static/" subdirectories and in STATICFILES_DIRS.
    # Example: "/home/media/media.lawrence.com/static/"
    STATIC_ROOT = values.Value(os.path.abspath(os.path.join(PROJECT_ROOT,
                                                            "..", "public")))

    # Additional locations of static files
    STATICFILES_DIRS = (
        os.path.join(PROJECT_ROOT, "static"),
    )
    # ########## URLs #################

    ROOT_URLCONF = values.Value('froide.urls')

    # URL prefix for static files.
    # Example: "http://media.lawrence.com/static/"

    # URL that handles the static files like app media.
    # Example: "http://media.lawrence.com"
    STATIC_URL = values.Value('/static/')

    USE_X_ACCEL_REDIRECT = values.BooleanValue(False)
    X_ACCEL_REDIRECT_PREFIX = values.Value('/protected')

    # ## URLs that can be translated to a secret value

    SECRET_URLS = values.DictValue({
        "admin": "admin"
    })

    # ######## Backends, Finders, Processors, Classes ####

    AUTH_USER_MODEL = values.Value('account.User')
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'froide.account.hashers.PBKDF2WrappedSHA1PasswordHasher',
    ]

    # List of finder classes that know how to find static files in
    # various locations.
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'django.contrib.staticfiles.finders.FileSystemFinder',
    )

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [
                os.path.join(PROJECT_ROOT, "templates"),
            ],
            'OPTIONS': {
                'debug': values.BooleanValue(DEBUG),
                'loaders': [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ],
                'builtins': ['overextends.templatetags.overextends_tags'],
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.i18n',
                    'django.template.context_processors.media',
                    'django.template.context_processors.static',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                    'froide.helper.context_processors.froide',
                    'froide.helper.context_processors.site_settings',
                    'froide.helper.context_processors.block_helper'
                ]
            }
        }
    ]

    MIDDLEWARE = [
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'oauth2_provider.middleware.OAuth2TokenMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]

    # ######### I18N and L10N ##################

    # Local time zone for this installation. Choices can be found here:
    # http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
    # although not all choices may be available on all operating systems.
    # On Unix systems, a value of None will cause Django to use the same
    # timezone as the operating system.
    # If running in a Windows environment this must be set to the same as your
    # system time zone.
    TIME_ZONE = values.Value('Europe/Berlin')
    USE_TZ = values.BooleanValue(True)

    # Language code for this installation. All choices can be found here:
    # http://www.i18nguy.com/unicode/language-identifiers.html
    LANGUAGE_CODE = values.Value('en')
    LANGUAGES = (
        ('en', _('English')),
        ('es', _('Spanish')),
        ('fi-fi', _('Finnish (Finland)')),
        ('de', _('German')),
        ('da-dk', _('Danish (Denmark)')),
        ('it', _('Italian')),
        ('pt', _('Portuguese')),
        ('sv-se', _('Swedish (Sweden)')),
        ('sv-fi', _('Swedish (Finland)')),
        ('zh-cn', _('Chinese (Simplified)')),
        ('zh-hk', _('Chinese (Traditional, Hong Kong)')),
    )

    # If you set this to False, Django will make some optimizations so as not
    # to load the internationalization machinery.
    USE_I18N = values.BooleanValue(True)

    # If you set this to False, Django will not format dates, numbers and
    # calendars according to the current locale
    USE_L10N = values.BooleanValue(True)

    DATE_FORMAT = values.Value("d. F Y")
    SHORT_DATE_FORMAT = values.Value("d.m.Y")
    DATE_INPUT_FORMATS = values.TupleValue(("%d.%m.%Y",))
    SHORT_DATETIME_FORMAT = values.Value("d.m.Y H:i")
    DATETIME_INPUT_FORMATS = values.TupleValue(("%d.%m.%Y %H:%M",))
    TIME_FORMAT = values.Value("H:i")
    TIME_INPUT_FORMATS = values.TupleValue(("%H:%M",))

    HOLIDAYS = [
        (1, 1),  # New Year's Day
        (12, 25),  # Christmas
        (12, 26)  # Second day of Christmas
    ]

    # Weekends are non-working days
    HOLIDAYS_WEEKENDS = True

    # Calculates other holidays based on easter sunday
    HOLIDAYS_FOR_EASTER = (0, -2, 1, 39, 50, 60)

    # ######## Logging ##########

    # A sample logging configuration.
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'root': {
            'level': 'WARNING',
            'handlers': [],
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            }
        },
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            },
        },
        'handlers': {
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
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
            'django.db.backends': {
                'level': 'ERROR',
                'handlers': ['console'],
                'propagate': False,
            }
        }
    }

    # ######## Security ###########

    CSRF_COOKIE_SECURE = False
    CSRF_FAILURE_VIEW = values.Value('froide.account.views.csrf_failure')

    # Change this
    # ALLOWED_HOSTS = ()
    ALLOWED_REDIRECT_HOSTS = ()

    SESSION_COOKIE_AGE = values.IntegerValue(3628800)  # six weeks
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False

    # ######## FilingCabinet Document ####

    # FILINGCABINET_DOCUMENT_MODEL = 'document.Document'
    # FILINGCABINET_DOCUMENTCOLLECTION_MODEL = 'document.DocumentCollection'

    FILINGCABINET_DOCUMENT_MODEL = 'document.Document'
    FILINGCABINET_DOCUMENTCOLLECTION_MODEL = 'document.DocumentCollection'

    # ######## Celery #############

    CELERY_BEAT_SCHEDULE = {
        'fetch-mail': {
            'task': 'froide.foirequest.tasks.fetch_mail',
            'schedule': crontab(),
        },
        'detect-asleep': {
            'task': 'froide.foirequest.tasks.detect_asleep',
            'schedule': crontab(hour=0, minute=0),
        },
        'detect-overdue': {
            'task': 'froide.foirequest.tasks.detect_overdue',
            'schedule': crontab(hour=0, minute=0),
        },
        'update-foirequestfollowers': {
            'task': 'froide.foirequestfollower.tasks.batch_update',
            'schedule': crontab(hour=0, minute=0),
        },
        'classification-reminder': {
            'task': 'froide.foirequest.tasks.classification_reminder',
            'schedule': crontab(hour=7, minute=0, day_of_week=6),
        },
    }

    CELERY_TASK_ALWAYS_EAGER = values.BooleanValue(True)

    CELERY_TASK_ROUTES = {
        'froide.foirequest.tasks.fetch_mail': {"queue": "emailfetch"},
        'froide.foirequest.tasks.process_mail': {"queue": "email"},
        'djcelery_email_send_multiple': {"queue": "email"},
    }
    CELERY_TIMEZONE = 'UTC'
    # We need to serialize email data as binary
    # which doesn't work well in JSON
    CELERY_TASK_SERIALIZER = 'pickle'
    CELERY_RESULT_SERIALIZER = 'pickle'
    CELERY_ACCEPT_CONTENT = ['pickle']

    CELERY_EMAIL_TASK_CONFIG = {
        'queue': 'email'
    }

    # ######## Haystack ###########

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
        }
    }

    # ######### API #########

    # Do not include xml by default, so lxml doesn't need to be present
    TASTYPIE_DEFAULT_FORMATS = ['json']

    OAUTH2_PROVIDER = {
        'SCOPES': {
            'read:user': _('Access to user status'),
            'read:profile': _('Read user profile information'),
            'read:email': _('Read user email'),
            'read:request': _('Read my (private) requests'),
            'make:request': _('Make requests on my behalf'),
        }
    }
    OAUTH2_PROVIDER_APPLICATION_MODEL = 'account.Application'

    LOGIN_URL = 'account-login'

    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework.authentication.SessionAuthentication',
            'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        ),
        'DEFAULT_PERMISSION_CLASSES': (
            'rest_framework.permissions.IsAuthenticatedOrReadOnly',
        ),
        'DEFAULT_PAGINATION_CLASS': 'froide.helper.api_utils.CustomLimitOffsetPagination',
        'PAGE_SIZE': 50,
        'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
            'froide.helper.api_renderers.CustomPaginatedCSVRenderer',
            'rest_framework.renderers.BrowsableAPIRenderer',
        )
    }

    # ######### Froide settings ########

    FROIDE_CONFIG = dict(
        user_can_hide_web=True,
        public_body_officials_public=True,
        public_body_officials_email_public=False,
        request_public_after_due_days=14,
        payment_possible=True,
        currency="Euro",
        default_law=1,
        search_engine_query="http://www.google.de/search?as_q=%(query)s&as_epq=&as_oq=&as_eq=&hl=en&lr=&cr=&as_ft=i&as_filetype=&as_qdr=all&as_occt=any&as_dt=i&as_sitesearch=%(domain)s&as_rights=&safe=images",
        greetings=[rec(r"Dear (?:Mr\.?|Mr?s\.? .*?)")],
        redact_salutation=r"(?:Mr\.?|Mr?s\.?)",
        custom_replacements=[],
        closings=[rec(r"Sincerely yours,?")],
        public_body_boosts={},
        autocomplete_body_boosts={},
        dryrun=False,
        read_receipt=False,
        delivery_receipt=False,
        dsn=False,
        delivery_reporter=None,
        request_throttle=None,  # Set to [(15, 7 * 24 * 60 * 60),] for 15 requests in 7 days
        dryrun_domain="testmail.example.com",
        allow_pseudonym=False,
        doc_conversion_binary=None,  # replace with libreoffice instance
        doc_conversion_call_func=None,  # see settings_test for use
        content_urls={
            'terms': '/terms/',
            'privary': '/privacy/',
            'about': '/about/',
            'help': '/help/',
        },
        message_handlers={
            'email': 'froide.foirequest.message_handlers.EmailMessageHandler'
        },
        auto_reply_subject_regex=rec('^(Auto-?Reply|Out of office)'),
        auto_reply_email_regex=rec('^auto(reply|responder)@')
    )

    TESSERACT_DATA_PATH = values.Value('/usr/local/share/tessdata')

    # ###### Email ##############

    # Django settings

    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_SUBJECT_PREFIX = values.Value('[Froide] ')
    SERVER_EMAIL = values.Value('error@example.com')
    DEFAULT_FROM_EMAIL = values.Value('info@example.com')

    # Official Notification Mail goes through
    # the normal Django SMTP Backend
    EMAIL_HOST = values.Value("")
    EMAIL_PORT = values.IntegerValue(587)
    EMAIL_HOST_USER = values.Value("")
    EMAIL_HOST_PASSWORD = values.Value("")
    EMAIL_USE_TLS = values.BooleanValue(True)

    # Custom backend that also requests Delivery Status
    FOI_EMAIL_BACKEND = 'froide.foirequest.smtp.FoiEmailBackend'
    # Froide special case settings
    # IMAP settings for fetching mail
    FOI_EMAIL_PORT_IMAP = values.IntegerValue(993)
    FOI_EMAIL_HOST_IMAP = values.Value("imap.example.com")
    FOI_EMAIL_ACCOUNT_NAME = values.Value("foi@example.com")
    FOI_EMAIL_ACCOUNT_PASSWORD = values.Value("")
    FOI_EMAIL_USE_SSL = values.BooleanValue(True)

    # SMTP settings for sending FoI mail
    FOI_EMAIL_HOST_USER = values.Value(FOI_EMAIL_ACCOUNT_NAME)
    FOI_EMAIL_HOST_FROM = values.Value(FOI_EMAIL_HOST_USER)
    FOI_EMAIL_HOST_PASSWORD = values.Value(FOI_EMAIL_ACCOUNT_PASSWORD)
    FOI_EMAIL_HOST = values.Value("smtp.example.com")
    FOI_EMAIL_PORT = values.IntegerValue(587)
    FOI_EMAIL_USE_TLS = values.BooleanValue(True)

    # The FoI Mail can use a different account
    FOI_EMAIL_DOMAIN = values.Value("example.com")

    FOI_EMAIL_TEMPLATE = None
    # Example:
    # FOI_EMAIL_TEMPLATE = lambda user_name, secret: "{username}.{secret}@{domain}" % (user_name, secret, FOI_EMAIL_DOMAIN)

    # Is the message you can send from fixed
    # or can you send from any address you like?
    FOI_EMAIL_FIXED_FROM_ADDRESS = values.BooleanValue(True)


class Dev(Base):
    pass


class Test(Base):
    DEBUG = False

    @property
    def TEMPLATES(self):
        TEMP = super(Test, self).TEMPLATES
        TEMP[0]['OPTIONS']['debug'] = True
        return TEMP

    def _fake_convert_pdf(self, infile, outpath):
        _, filename = os.path.split(infile)
        name, ext = filename.rsplit('.', 1)
        output = os.path.join(outpath, '%s.pdf' % name)
        args = ['cp', infile, output]
        return args, output

    @property
    def FROIDE_CONFIG(self):
        config = dict(super(Test, self).FROIDE_CONFIG)
        config.update(dict(
            doc_conversion_call_func=self._fake_convert_pdf,
            default_law=10000,
            greetings=[rec(r"Dear ((?:Mr\.?|Ms\.?) .*),?"), rec(r'Sehr geehrter? ((Herr|Frau) .*),?')],
            closings=[rec(r"Sincerely yours,?"), rec(r'Mit freundlichen Grüßen')],
            public_body_officials_public=False
        ))
        return config

    @property
    def MEDIA_ROOT(self):
        return os.path.abspath(os.path.join(super(Test, self).PROJECT_ROOT, "tests", "testdata"))

    MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
    CACHES = values.CacheURLValue('locmem://')

    TEST_SELENIUM_DRIVER = values.Value('chrome_headless')

    SECRET_URLS = values.DictValue({
        "admin": "admin",
        "postmark_inbound": "postmark_inbound",
        "postmark_bounce": "postmark_bounce"
    })

    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'info@example.com'

    FOI_EMAIL_DOMAIN = 'fragdenstaat.de'

    @property
    def HAYSTACK_CONNECTIONS(self):
        return {
            'default': {
                'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
                'PATH': os.path.join(super(Test, self).PROJECT_ROOT, 'tests/froide_test_whoosh_db'),
            },
        }

    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

    MIDDLEWARE = [
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ]


class CustomTest(Test):
    pass


class German(object):
    LANGUAGE_CODE = "de"
    LANGUAGES = (
        ('de', _('German')),
    )

    DATE_FORMAT = "d. F Y"
    SHORT_DATE_FORMAT = "d.m.Y"
    DATE_INPUT_FORMATS = ("%d.%m.%Y",)
    SHORT_DATETIME_FORMAT = "d.m.Y H:i"
    DATETIME_INPUT_FORMATS = ("%d.%m.%Y %H:%M",)
    TIME_FORMAT = "H:i"
    TIME_INPUT_FORMATS = ("%H:%M",)

    # Holidays Germany
    HOLIDAYS = [
        (1, 1),  # New Year's Day
        (5, 1),  # Labour Day
        (10, 3),  # Day of German reunification
        (12, 25),  # Christmas
        (12, 26),  # Second day of Christmas
    ]

    # Weekends are non-working days
    HOLIDAYS_WEEKENDS = True

    # Calculates other holidays based on easter sunday
    HOLIDAYS_FOR_EASTER = (0, -2, 1, 39, 50, 60)

    @property
    def FROIDE_CONFIG(self):
        german_config = dict(super(German, self).FROIDE_CONFIG)
        german_config.update({
            "payment_possible": True,
            "currency": "Euro",
            "public_body_boosts": {
                "Oberste Bundesbeh\xf6rde": 1.9,
                "Obere Bundesbeh\xf6rde": 1.1,
                "Ministerium": 1.8,
                "Senatsverwaltung": 1.8,
                "Kommunalverwaltung": 1.7,
                "Andere": 0.8
            },
            "autocomplete_body_boosts": {
                "Bund": 1.5
            },
            'greetings': [rec(r"Sehr geehrt(er? (?:Herr|Frau)(?: ?Dr\.?)?(?: ?Prof\.?)? .*)")],
            'redact_salutation': r"(?:er?\s+)?(?:Herr|Frau)",
            'closings': [rec(r"Mit freundlichen Gr\xfc\xdfen,?"), rec(r"Mit den besten Grüßen,?")]
        })
        return german_config


class Production(Base):
    DEBUG = False

    @property
    def TEMPLATES(self):
        TEMP = super(Production, self).TEMPLATES
        TEMP[0]['OPTIONS']['debug'] = False
        return TEMP

    ALLOWED_HOSTS = values.TupleValue(('example.com',))
    CELERY_TASK_ALWAYS_EAGER = values.BooleanValue(False)
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'


class SSLSite(object):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True


class NginxSecureStatic(object):
    USE_X_ACCEL_REDIRECT = True
    X_ACCEL_REDIRECT_PREFIX = values.Value('/protected')


class SSLNginxProduction(SSLSite, NginxSecureStatic, Production):
    pass


class AmazonS3(object):
    STATICFILES_STORAGE = values.Value('storages.backends.s3boto.S3BotoStorage')

    STATIC_URL = values.Value('/static/')

    DEFAULT_FILE_STORAGE = values.Value('storages.backends.s3boto.S3BotoStorage')

    AWS_ACCESS_KEY_ID = values.Value('')
    AWS_SECRET_ACCESS_KEY = values.Value('')
    AWS_STORAGE_BUCKET_NAME = values.Value('')
    AWS_S3_SECURE_URLS = values.Value(False)
    AWS_QUERYSTRING_AUTH = values.Value(False)


class Heroku(Production):
    ALLOWED_HOSTS = ['*']
    SECRET_KEY = values.SecretValue()

    CELERY_TASK_ALWAYS_EAGER = values.BooleanValue(True)
    CELERY_BROKER_URL = values.Value('amqp://')

    @property
    def LOGGING(self):
        logging = super(Heroku, self).LOGGING
        logging['handlers']['console']['stream'] = sys.stdout
        logging['loggers']['django.request']['handlers'] = ['console']
        return logging


def os_env(name):
    return os.environ.get(name)


class HerokuPostmark(Heroku):
    SECRET_URLS = values.DictValue({
        "admin": "admin",
        "postmark_inbound": "postmark_inbound",
        "postmark_bounce": "postmark_bounce"
    })

    FOI_EMAIL_TEMPLATE = values.Value('request+{secret}@{domain}')
    FOI_EMAIL_DOMAIN = values.Value('inbound.postmarkapp.com')

    SERVER_EMAIL = values.Value(os_env('POSTMARK_INBOUND_ADDRESS'))
    DEFAULT_FROM_EMAIL = values.Value(os_env('POSTMARK_INBOUND_ADDRESS'))

    # Official Notification Mail goes through
    # the normal Django SMTP Backend
    EMAIL_HOST = os_env('POSTMARK_SMTP_SERVER')
    EMAIL_PORT = values.IntegerValue(2525)
    EMAIL_HOST_USER = os_env('POSTMARK_API_KEY')
    EMAIL_HOST_PASSWORD = os_env('POSTMARK_API_KEY')
    EMAIL_USE_TLS = values.BooleanValue(True)

    # SMTP settings for sending FoI mail
    FOI_EMAIL_FIXED_FROM_ADDRESS = values.BooleanValue(False)
    FOI_EMAIL_HOST_FROM = os_env('POSTMARK_INBOUND_ADDRESS')
    FOI_EMAIL_HOST_USER = os_env('POSTMARK_API_KEY')
    FOI_EMAIL_HOST_PASSWORD = os_env('POSTMARK_API_KEY')
    FOI_EMAIL_HOST = os_env('POSTMARK_SMTP_SERVER')
    FOI_EMAIL_PORT = values.IntegerValue(2525)
    FOI_EMAIL_USE_TLS = values.BooleanValue(True)


class HerokuPostmarkS3(AmazonS3, HerokuPostmark):
    pass


class HerokuSSL(SSLSite, Heroku):
    pass


class HerokuSSLPostmark(SSLSite, HerokuPostmark):
    pass


try:
    from .local_settings import *  # noqa
except ImportError:
    pass
