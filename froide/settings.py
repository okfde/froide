# -*- coding: utf-8 -*-
from configurations import Configuration, importer, values
importer.install(check_options=True)

import os
import sys
import re

rec = lambda x: re.compile(x, re.I | re.U)

gettext = lambda s: s

# Django settings for froide project.


class Base(Configuration):
    DEBUG = values.BooleanValue(True)
    TEMPLATE_DEBUG = values.BooleanValue(DEBUG)

    DATABASES = values.DatabaseURLValue('sqlite:///dev.db')
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

        # external
        'haystack',
        'djcelery',
        'taggit',
        'floppyforms',
        'overextends',
        'tastypie',
        'tastypie_swagger',
        'storages',
        'compressor',

        # local
        'froide.foirequest',
        'froide.foirequestfollower',
        'froide.frontpage',
        'froide.publicbody',
        'froide.account',
        'froide.redaction',
        'froide.foisite',
        'froide.helper',
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
    MEDIA_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "files"))

    # Sub path in MEDIA_ROOT that will hold FOI attachments
    FOI_MEDIA_PATH = values.Value('foi')

    # Absolute path to the directory static files should be collected to.
    # Don't put anything in this directory yourself; store your static files
    # in apps' "static/" subdirectories and in STATICFILES_DIRS.
    # Example: "/home/media/media.lawrence.com/static/"
    STATIC_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "public"))

    # Additional locations of static files
    STATICFILES_DIRS = (
        os.path.join(PROJECT_ROOT, "static"),
    )
    COMPRESS_ENABLED = values.BooleanValue(False)
    COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
    COMPRESS_CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter',
                            'compressor.filters.cssmin.CSSMinFilter']
    COMPRESS_PARSER = 'compressor.parser.HtmlParser'

    # Additional locations of template files
    TEMPLATE_DIRS = (
        os.path.join(PROJECT_ROOT, "templates"),
    )

    # ########## URLs #################

    ROOT_URLCONF = values.Value('froide.urls')

    # URL that handles the media served from MEDIA_ROOT. Make sure to use a
    # trailing slash.
    # Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
    MEDIA_URL = values.Value('/files/')

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
    CUSTOM_AUTH_USER_MODEL_DB = values.Value('')

    # List of finder classes that know how to find static files in
    # various locations.
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'compressor.finders.CompressorFinder',
    )

    AUTHENTICATION_BACKENDS = [
        "froide.helper.auth.EmailBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]

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
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
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
    LANGUAGE_CODE = values.Value('en-us')
    LANGUAGES = (
        ('en', gettext('English')),
        ('es', gettext('Spanish')),
        ('fi-fi', gettext('Finnish (Finland)')),
        ('de', gettext('German')),
        ('da-dk', gettext('Danish (Denmark)')),
        ('it', gettext('Italian')),
        ('pt', gettext('Portuguese')),
        ('sv-se', gettext('Swedish (Sweden)')),
        ('sv-fi', gettext('Swedish (Finland)')),
        ('zh-cn', gettext('Chinese (Simplified)')),
        ('zh-hk', gettext('Chinese (Traditional, Hong Kong)')),
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
    CSRF_COOKIE_HTTPONLY = True
    CSRF_FAILURE_VIEW = values.Value('froide.account.views.csrf_failure')

    # Change this
    # ALLOWED_HOSTS = ()

    SESSION_COOKIE_AGE = values.IntegerValue(3628800)  # six weeks
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False

    # ######## Celery #############

    CELERY_RESULT_BACKEND = values.Value('djcelery.backends.database:DatabaseBackend')
    CELERYBEAT_SCHEDULER = values.Value("djcelery.schedulers.DatabaseScheduler")
    CELERY_ALWAYS_EAGER = values.BooleanValue(True)

    CELERY_ROUTES = {
        'froide.foirequest.tasks.fetch_mail': {"queue": "emailfetch"},
    }

    # ######## Haystack ###########

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
        }
    }

    # ######### Tastypie #########

    TASTYPIE_SWAGGER_API_MODULE = values.Value('froide.urls.v1_api')

    # ######### Froide settings ########

    FROIDE_THEME = None

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
        doc_conversion_call_func=None,  # see settings_test for use
    )

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
    FOI_EMAIL_PORT = values.IntegerValue(537)
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


class ThemeBase(object):

    @property
    def INSTALLED_APPS(self):
        installed = super(ThemeBase, self).INSTALLED_APPS
        installed.default += [
            self.FROIDE_THEME
        ]
        return installed.default

    @property
    def TEMPLATE_LOADERS(self):
        old = super(ThemeBase, self).TEMPLATE_LOADERS
        if self.FROIDE_THEME is not None:
            return (['froide.helper.theme_utils.ThemeLoader'] + old)
        return old


class Test(Base):
    DEBUG = False
    TEMPLATE_DEBUG = True

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
            greetings=[rec(u"Dear ((?:Mr\.?|Ms\.?) .*),?"), rec(u'Sehr geehrter? ((Herr|Frau) .*),?')],
            closings=[rec(u"Sincerely yours,?"), rec(u'Mit freundlichen Grüßen')],
            public_body_officials_public=False
        ))
        return config

    @property
    def MEDIA_ROOT(self):
        return os.path.abspath(os.path.join(super(Test, self).PROJECT_ROOT, "tests", "testdata"))

    MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
    CACHES = values.CacheURLValue('locmem://')

    TEST_SELENIUM_DRIVER = values.Value('phantomjs')

    USE_X_ACCEL_REDIRECT = True

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

    CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
    CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

    MIDDLEWARE_CLASSES = [
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ]


class German(object):
    LANGUAGE_CODE = "de"
    LANGUAGES = (
        ('de', gettext('German')),
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
                u"Oberste Bundesbeh\xf6rde": 1.9,
                u"Obere Bundesbeh\xf6rde": 1.1,
                u"Ministerium": 1.8,
                u"Senatsverwaltung": 1.8,
                u"Kommunalverwaltung": 1.7,
                u"Andere": 0.8
            },
            'greetings': [rec(u"Sehr geehrt(er? (?:Herr|Frau)(?: ?Dr\.?)?(?: ?Prof\.?)? .*)")],
            'closings': [rec(u"Mit freundlichen Gr\xfc\xdfen,?"), rec("Mit den besten Gr\xfc\xdfen,?")]
        })
        return german_config


class Production(Base):
    DEBUG = False
    TEMPLATE_DEBUG = False
    ALLOWED_HOSTS = values.TupleValue(('example.com',))
    CELERY_ALWAYS_EAGER = values.BooleanValue(False)
    COMPRESS_ENABLED = values.BooleanValue(True)
    COMPRESS_OFFLINE = values.BooleanValue(True)


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
    STATICFILES_STORAGE = values.Value('froide.helper.storage_utils.CachedS3BotoStorage')
    COMPRESS_STORAGE = values.Value('froide.helper.storage_utils.CachedS3BotoStorage')

    STATIC_URL = values.Value('/static/')
    COMPRESS_URL = values.Value(STATIC_URL)

    DEFAULT_FILE_STORAGE = values.Value('storages.backends.s3boto.S3BotoStorage')

    AWS_ACCESS_KEY_ID = values.Value('')
    AWS_SECRET_ACCESS_KEY = values.Value('')
    AWS_STORAGE_BUCKET_NAME = values.Value('')
    AWS_S3_SECURE_URLS = values.Value(False)
    AWS_QUERYSTRING_AUTH = values.Value(False)


class Heroku(Production):
    ALLOWED_HOSTS = ['*']
    SECRET_KEY = values.SecretValue()

    CELERY_ALWAYS_EAGER = values.BooleanValue(True)
    BROKER_URL = values.Value('amqp://')

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
