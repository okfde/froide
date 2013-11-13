# -*- coding: utf-8 -*-
# Django settings for froide project.
import os.path
import re

########### Basic Stuff ###############

DEBUG = True

TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.comments',

    # external
    'south',
    'haystack',
    'djcelery',
    'djcelery_email',
    'debug_toolbar',
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
    'froide.helper',
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}


############## Site Configuration #########

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'make_me_unique!!'

SITE_NAME = 'Froide'
SITE_EMAIL = 'info@example.com'
SITE_URL = 'http://localhost:8000'

SITE_ID = 1

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

INTERNAL_IPS = ('127.0.0.1',)

############### PATHS ###############

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

LOCALE_PATHS = (
    os.path.join(PROJECT_ROOT, '..', "locale"),
)

GEOIP_PATH = None

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "..", "files")

# Sub path in MEDIA_ROOT that will hold FOI attachments
FOI_MEDIA_PATH = 'foi'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, "..", "public")

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, "static"),
)

# Additional locations of template files
TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, "templates"),
)

########### URLs #################

ROOT_URLCONF = 'froide.urls'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/files/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"

# URL that handles the static files like app media.
# Example: "http://media.lawrence.com"
STATIC_URL = "/static/"

USE_X_ACCEL_REDIRECT = False
X_ACCEL_REDIRECT_PREFIX = '/protected'

### URLs that can be translated to a secret value

SECRET_URLS = {
    "admin": "admin"
}


######### Backends, Finders, Processors, Classes ####

AUTH_PROFILE_MODULE = 'account.Profile'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)


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
TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'djangosecure.middleware.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'pagination.middleware.PaginationMiddleware',
]
MIDDLEWARE_CLASSES += ['debug_toolbar.middleware.DebugToolbarMiddleware']

########## Debug ###########

DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False
}

########## I18N and L10N ##################

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'
USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'fi-FI'


# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True


# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

DATE_FORMAT = "d. F Y"
SHORT_DATE_FORMAT = "d.m.Y"
DATE_INPUT_FORMATS = ("%d.%m.%Y",)
SHORT_DATETIME_FORMAT = "d.m.Y H:i"
DATETIME_INPUT_FORMATS = ("%d.%m.%Y %H:%M",)
TIME_FORMAT = "H:i"
TIME_INPUT_FORMATS = ("%H:%M",)

# Holidays in your country

HOLIDAYS = [
    (1, 1),  # New Year's Day
    (12, 25),  # Christmas
    (12, 26)  # Second day of Christmas
]

# Weekends are non-working days
HOLIDAYS_WEEKENDS = True

# Calculates other holidays based on easter sunday
HOLIDAYS_FOR_EASTER = (0, -2, 1, 39, 50, 60)


######### Logging ##########

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


######### Security ###########

CSRF_COOKIE_SECURE = False
CSRF_FAILURE_VIEW = 'froide.account.views.csrf_failure'

# Change this
# ALLOWED_HOSTS = ()

SESSION_COOKIE_AGE = 3628800  # six weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False

# Django-Secure options
SECURE_FRAME_DENY = True


######### South #############

SOUTH_TESTS_MIGRATE = False


######### Celery #############

import djcelery
djcelery.setup_loader()

CELERY_RESULT_BACKEND = "database"
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_ALWAYS_EAGER = True

######### Haystack ###########

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    }
}
HAYSTACK_SIGNAL_PROCESSOR = 'celery_haystack.signals.CelerySignalProcessor'

########## Froide settings ########

FROIDE_THEME = None

TASTYPIE_SWAGGER_API_MODULE = 'froide.urls.v1_api'


rec = re.compile

FROIDE_CONFIG = dict(
    create_new_publicbody=True,
    publicbody_empty=True,
    user_can_hide_web=True,
    public_body_officials_public=True,
    public_body_officials_email_public=False,
    request_public_after_due_days=14,
    payment_possible=True,
    currency="Euro",
    default_law=1,
    search_engine_query="http://www.google.de/search?as_q=%(query)s&as_epq=&as_oq=&as_eq=&hl=en&lr=&cr=&as_ft=i&as_filetype=&as_qdr=all&as_occt=any&as_dt=i&as_sitesearch=%(domain)s&as_rights=&safe=images",
    greetings=[rec(u"Dear (?:Mr\.?|Ms\.? .*?)")],
    closings=[rec(u"Sincerely yours,?")],
    public_body_boosts={},
    dryrun=False,
    dryrun_domain="testmail.example.com",
    allow_pseudonym=False,
    doc_conversion_binary=None,  # replace with libreoffice instance
    doc_conversion_call_func=None  # see settings_test for use
)


####### Email ##############

# Django settings

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_SUBJECT_PREFIX = '[Froide] '
SERVER_EMAIL = 'error@example.com'
DEFAULT_FROM_EMAIL = 'info@example.com'

# Official Notification Mail goes through
# the normal Django SMTP Backend
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = True

# Froide special case settings
# IMAP settings for fetching mail
FOI_EMAIL_PORT_IMAP = 993
FOI_EMAIL_HOST_IMAP = "imap.example.com"
FOI_EMAIL_ACCOUNT_NAME = "foi@example.com"
FOI_EMAIL_ACCOUNT_PASSWORD = ""
FOI_EMAIL_USE_SSL = True


# SMTP settings for setting FoI mail
# like Django
FOI_EMAIL_HOST_USER = FOI_EMAIL_ACCOUNT_NAME
FOI_EMAIL_HOST_FROM = FOI_EMAIL_HOST_USER
FOI_EMAIL_HOST_PASSWORD = FOI_EMAIL_ACCOUNT_PASSWORD
FOI_EMAIL_HOST = "smtp.example.com"
FOI_EMAIL_PORT = 537
FOI_EMAIL_USE_TLS = True

# The FoI Mail can use a different account
FOI_EMAIL_DOMAIN = "example.com"

FOI_EMAIL_FUNC = None
# Example:
# FOI_EMAIL_FUNC = lambda user_name, secret: "%s.%s@%s" % (user_name, secret, FOI_EMAIL_DOMAIN)

# Is the message you can send from fixed
# or can you send from any address you like?
FOI_EMAIL_FIXED_FROM_ADDRESS = True
