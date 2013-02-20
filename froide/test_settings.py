# -*- coding: utf-8 -*-
# Django settings for froide project.
import os.path
import re

DEBUG = False

TEMPLATE_DEBUG = True

FROIDE_THEME = None

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

ADMINS = (
    ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

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

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#         'NAME': 'fragdenstaat',                      # Or path to database file if using sqlite3.
#         'USER': 'fragdenstaat',                      # Not used with sqlite3.
#         'PASSWORD': '',                  # Not used with sqlite3.
#         'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#         'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
#         'OPTIONS': {
#             'autocommit': True,
#         }
#     }
# }

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'
USE_TZ = True


LOCALE_PATHS = (
    os.path.join(PROJECT_ROOT, "locale"),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "..", "files")

GEOIP_PATH = None

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/files/'

FOI_MEDIA_PATH = 'foi'

USE_X_ACCEL_REDIRECT = True
X_ACCEL_REDIRECT_PREFIX = '/protected'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"

STATIC_ROOT = os.path.join(PROJECT_ROOT, "..", "public")

# URL that handles the static files like app media.
# Example: "http://media.lawrence.com"
STATIC_URL = "/static/"

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, "static"),
)


# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

FIXTURE_DIRS = [
    os.path.join(PROJECT_ROOT, "fixtures"),
]

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'ds96-%ufkm==%083c8td#w$=9e3w0$l61gj-83*qi^cm63_a_j'

AUTHENTICATION_BACKENDS = (
    "froide.helper.auth.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'froide.helper.context_processors.froide',
    'froide.helper.context_processors.site_settings'
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

ROOT_URLCONF = 'froide.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.markup',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django.contrib.databrowse',
    'django.contrib.comments',

    # external
    'south',
    'haystack',
    'djcelery',
    'djcelery_email',
    'kombu.transport.django',
    'debug_toolbar',
    'raven.contrib.django',
    'raven.contrib.django.celery',
    'celery_haystack',
    'pagination',
    'djangosecure',
    'taggit',
    'django_gravatar',
    'floppyforms',
    'overextends',
    'tastypie',
    'tastypie_swagger',

    # local
    'froide.foirequest',
    'froide.foirequestfollower',
    'froide.frontpage',
    'froide.publicbody',
    'froide.account',
    'froide.foiidea',
    'froide.redaction',
    'froide.foisite',
)

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
        'sentry.errors': {
            'level': 'DEBUG',
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
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': True
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

SESSION_COOKIE_AGE = 3628800  # six weeks

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

CACHES = {
    'default': {
        # 'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

TEST_RUNNER = 'discover_runner.DiscoverRunner'

# south settings

SOUTH_TESTS_MIGRATE = False

EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'

DEFAULT_FROM_EMAIL = 'info@fragdenstaat.de'

HOLIDAYS = [
    (1, 1),  # New Year's Day
    (5, 1),  # Labour Day
    (10, 3),  # German Unity Day
    (12, 25),  # Christmas
    (12, 26)  # Second day of Christmas
]

# Weekends are non-working days
HOLIDAYS_WEEKENDS = True

# Calculates other German holidays based on easter sunday
HOLIDAYS_FOR_EASTER = (0, -2, 1, 39, 50, 60)

FROIDE_DRYRUN = False
FROIDE_DRYRUN_DOMAIN = "fragdenstaat.stefanwehrmeyer.com"

AUTH_PROFILE_MODULE = 'account.Profile'

SEARCH_ENGINE_QUERY = "http://www.google.de/search?as_q=%(query)s&as_epq=&as_oq=&as_eq=&hl=de&lr=&cr=&as_ft=i&as_filetype=&as_qdr=all&as_occt=any&as_dt=i&as_sitesearch=%(domain)s&as_rights=&safe=images"

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'froide',
    },
}

# Official Notification Mail goes through
# the normal Django SMTP Backend
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = True

# The FoI Mail can use a different account
FOI_EMAIL_DOMAIN = "fragdenstaat.de"
# IMAP settings for fetching mail
FOI_EMAIL_PORT_IMAP = 993
FOI_EMAIL_HOST_IMAP = "imap.example.com"
FOI_EMAIL_ACCOUNT_NAME = "foi@example.com"
FOI_EMAIL_ACCOUNT_PASSWORD = ""
FOI_EMAIL_USE_SSL = True

# Is the message you can send from fixed
# or can you send from any address you like?
FOI_EMAIL_FIXED_FROM_ADDRESS = True

# SMTP settings for setting FoI mail
# like Django
FOI_EMAIL_HOST_USER = FOI_EMAIL_ACCOUNT_NAME
FOI_EMAIL_HOST_FROM = FOI_EMAIL_HOST_USER
FOI_EMAIL_HOST_PASSWORD = FOI_EMAIL_ACCOUNT_PASSWORD
FOI_EMAIL_HOST = "smtp.example.com"
FOI_EMAIL_PORT = 537
FOI_EMAIL_USE_TLS = True


import djcelery
djcelery.setup_loader()

CELERY_RESULT_BACKEND = "database"
CELERY_RESULT_DBURI = "sqlite:///dev.db"

CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_ALWAYS_EAGER = True

# local settings

LANGUAGE_CODE = "en"

DATE_FORMAT = "d. F Y"
SHORT_DATE_FORMAT = "d.m.Y"
DATE_INPUT_FORMATS = ("%d.%m.%Y",)
SHORT_DATETIME_FORMAT = "d.m.Y H:i"
DATETIME_INPUT_FORMATS = ("%d.%m.%Y %H:%M",)
TIME_FORMAT = "H:i"
TIME_INPUT_FORMATS = ("%H:%M",)

ADMINS = (
    ('Stefan Wehrmeyer', 'mail@stefanwehrmeyer.com'),
)
INTERNAL_IPS = ('127.0.0.1',)


MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'pagination.middleware.PaginationMiddleware',
]
MIDDLEWARE_CLASSES += ['debug_toolbar.middleware.DebugToolbarMiddleware']

SITE_NAME = "Frag den Staat"
SITE_EMAIL = "info@example.com"
SITE_URL = 'http://localhost:8000'

rec = re.compile
POSSIBLE_GREETINGS = [rec(u"Sehr geehrt(er? (?:Herr|Frau) .*)")]
POSSIBLE_CLOSINGS = [rec(u"Mit freundlichen Gr\xfc\xdfen,?")]


TWITTER_CONSUMER_KEY = "4yuJF1vAnAYU0THU4v6ZPQ"
TWITTER_CONSUMER_SECRET = "sW9tWul2La2UpULVCEqFs7t1o3lczKqvM4LwFvup1SI"
TWITTER_ACCESS_KEY = '297351336-OrhX7oQHwSHMYBUO3A0i4GT9Ws6COBwaGcjVZtwM'
TWITTER_ACCESS_SECRET = '2fCvKbooTtzodKW4uVknY3MVkmYVWbxLuBs5fKHcnI'


SECRET_URLS = {
    "admin": "admin"
}

FROIDE_CONFIG = {
    "create_new_publicbody": True,
    "publicbody_empty": True,
    "user_can_hide_web": True,
    "public_body_officials_public": False,
    "public_body_officials_email_public": False,
    "payment_possible": True,
    "currency": "Euro",
    "default_law": 2
}

FROIDE_PUBLIC_BODY_BOOSTS = {
    u"Oberste Bundesbehörde": 1.9,
    u"Obere Bundesbehörde": 1.1,
    u"Andere": 0.8
}

# dev use:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
