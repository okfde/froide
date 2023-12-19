import os
import re
from pathlib import Path

from django.utils.translation import gettext_lazy as _

from configurations import Configuration, importer, values

from celery.schedules import crontab

importer.install(check_options=True)


def rec(x: str) -> re.Pattern:
    return re.compile(x, re.I | re.U)


class Base(Configuration):
    DEBUG = values.BooleanValue(True)
    CONN_MAX_AGE = None

    INSTALLED_APPS = values.ListValue(
        [
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.sites",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            "django.contrib.admin",
            "django_comments",
            "django.contrib.flatpages",
            "django.contrib.sitemaps",
            "django.contrib.humanize",
            "django.contrib.gis",
            "channels",
            # overwrite management command in
            # django_elasticsearch_dsl
            "froide.helper",
            # external
            "django_elasticsearch_dsl",
            "taggit",
            "storages",
            "treebeard",
            "parler",
            "django_filters",
            "leaflet",
            "django_json_widget",
            "django_celery_beat",
            "mfa",
            "easy_thumbnails",
            # local
            "froide.foirequest",
            "froide.follow",
            "froide.foirequestfollower",  # needs to come after foirequest
            "froide.frontpage",
            "froide.georegion",
            "froide.publicbody",
            "froide.document",
            "froide.letter",
            "froide.account",
            "froide.bounce",
            "froide.team",
            "froide.foisite",
            "froide.problem",
            "froide.accesstoken",
            "froide.proof",
            "froide.guide",
            "froide.comments",
            "froide.campaign",
            "froide.organization",
            "froide.upload",
            # Semi-external
            "filingcabinet",  # Later in template chain than froide.document
            # API
            "oauth2_provider",
            "rest_framework",
            "drf_spectacular",
            "drf_spectacular_sidecar",
        ]
    )

    DATABASES = values.DatabaseURLValue("postgis://froide:froide@127.0.0.1:5432/froide")
    DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }

    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

    # ############# Site Configuration #########

    # Make this unique, and don't share it with anybody.
    SECRET_KEY = "make_me_unique!!"

    SITE_NAME = values.Value("Froide")
    SITE_LOGO = values.Value("")
    SITE_EMAIL = values.Value("info@froide.example.com")
    SITE_URL = values.Value("http://localhost:8000")

    @property
    def MFA_DOMAIN(self):
        return self.SITE_URL.rsplit("/", 1)[1]

    @property
    def MFA_SITE_TITLE(self):
        return self.SITE_NAME

    SITE_ID = values.IntegerValue(1)

    ADMINS = (
        # ('Your Name', 'your_email@example.com'),
    )

    MANAGERS = ADMINS

    INTERNAL_IPS = values.TupleValue(("127.0.0.1",))

    # ############## PATHS ###############

    PROJECT_ROOT = Path(__file__).resolve().parent
    BASE_DIR = PROJECT_ROOT.parent

    LOCALE_PATHS = [BASE_DIR / "locale"]

    GEOIP_PATH = None
    GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH")
    GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH")

    # Absolute filesystem path to the directory that will hold user-uploaded files.
    # Example: "/home/media/media.lawrence.com/media/"
    MEDIA_ROOT = values.Value(BASE_DIR / "files")

    # URL that handles the media served from MEDIA_ROOT. Make sure to use a
    # trailing slash.
    # Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
    MEDIA_URL = values.Value("/files/")

    # Sub path in MEDIA_ROOT that will hold FOI attachments
    FOI_MEDIA_PATH = values.Value("foi")
    FOI_MEDIA_TOKEN_EXPIRY = 2 * 60
    INTERNAL_MEDIA_PREFIX = values.Value("/protected/")

    # Absolute path to the directory static files should be collected to.
    # Don't put anything in this directory yourself; store your static files
    # in apps' "static/" subdirectories and in STATICFILES_DIRS.
    # Example: "/home/media/media.lawrence.com/static/"
    STATIC_ROOT = values.Value(BASE_DIR / "public")

    FRONTEND_BUILD_DIR = BASE_DIR / "build"
    FRONTEND_SERVER_URL = "http://localhost:5173/static/"

    @property
    def FRONTEND_DEBUG(self):
        return self.DEBUG

    # Additional locations of static files

    @property
    def STATICFILES_DIRS(self):
        return [self.FRONTEND_BUILD_DIR, self.BASE_DIR / "froide" / "static"]

    # ########## URLs #################

    ROOT_URLCONF = values.Value("froide.urls")
    ASGI_APPLICATION = "froide.routing.application"

    # URL prefix for static files.
    # Example: "http://media.lawrence.com/static/"

    # URL that handles the static files like app media.
    # Example: "http://media.lawrence.com"
    STATIC_URL = values.Value("/static/")

    # ## URLs that can be translated to a secret value

    SECRET_URLS = values.DictValue({"admin": "admin"})

    # ######## Backends, Finders, Processors, Classes ####

    AUTH_USER_MODEL = values.Value("account.User")
    AUTHENTICATION_BACKENDS = [
        "django.contrib.auth.backends.ModelBackend",
        "froide.foirequest.auth_backend.FoiRequestAuthBackend",
    ]
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
        "froide.account.hashers.PBKDF2WrappedSHA1PasswordHasher",
    ]
    MIN_PASSWORD_LENGTH = 9
    AUTH_PASSWORD_VALIDATORS = [
        {
            "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            "OPTIONS": {
                "min_length": MIN_PASSWORD_LENGTH,
            },
        },
        {
            "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
        },
    ]

    # List of finder classes that know how to find static files in
    # various locations.
    STATICFILES_FINDERS = (
        "django.contrib.staticfiles.finders.FileSystemFinder",
        "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    )

    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [
                PROJECT_ROOT / "templates",
            ],
            "OPTIONS": {
                "debug": values.BooleanValue(DEBUG),
                "loaders": [
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ],
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.i18n",
                    "django.template.context_processors.media",
                    "django.template.context_processors.static",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                    "froide.helper.context_processors.froide",
                    "froide.helper.context_processors.site_settings",
                    "froide.helper.context_processors.block_helper",
                ],
            },
        }
    ]

    MIDDLEWARE = [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.locale.LocaleMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "oauth2_provider.middleware.OAuth2TokenMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]

    X_FRAME_OPTIONS = "SAMEORIGIN"

    COMMENTS_APP = "froide.comments"

    # ######### I18N and L10N ##################

    # Local time zone for this installation. Choices can be found here:
    # http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
    # although not all choices may be available on all operating systems.
    # On Unix systems, a value of None will cause Django to use the same
    # timezone as the operating system.
    # If running in a Windows environment this must be set to the same as your
    # system time zone.
    TIME_ZONE = values.Value("Europe/Berlin")
    USE_TZ = values.BooleanValue(True)

    # Language code for this installation. All choices can be found here:
    # http://www.i18nguy.com/unicode/language-identifiers.html
    LANGUAGE_CODE = values.Value("en")
    LANGUAGES = (
        ("en", _("English")),
        ("es", _("Spanish")),
        ("fi-fi", _("Finnish (Finland)")),
        ("de", _("German")),
        ("da-dk", _("Danish (Denmark)")),
        ("it", _("Italian")),
        ("pt", _("Portuguese")),
        ("sv-se", _("Swedish (Sweden)")),
        ("sv-fi", _("Swedish (Finland)")),
        ("zh-cn", _("Chinese (Simplified)")),
        ("zh-hk", _("Chinese (Traditional, Hong Kong)")),
    )

    # If you set this to False, Django will make some optimizations so as not
    # to load the internationalization machinery.
    USE_I18N = values.BooleanValue(True)

    DATE_FORMAT = values.Value("d. F Y")
    SHORT_DATE_FORMAT = values.Value("d.m.Y")
    DATE_INPUT_FORMATS = values.TupleValue(("%d.%m.%Y",))
    DATETIME_FORMAT = values.Value("N j, Y, P")
    SHORT_DATETIME_FORMAT = values.Value("d.m.Y H:i")
    DATETIME_INPUT_FORMATS = values.TupleValue(("%d.%m.%Y %H:%M",))
    TIME_FORMAT = values.Value("H:i")
    TIME_INPUT_FORMATS = values.TupleValue(("%H:%M:%S", "%H:%M"))

    TAGGIT_CASE_INSENSITIVE = True
    TAGGIT_STRIP_UNICODE_WHEN_SLUGIFYING = True

    HOLIDAYS = [
        (1, 1),  # New Year's Day
        (12, 25),  # Christmas
        (12, 26),  # Second day of Christmas
    ]

    # Weekends are non-working days
    HOLIDAYS_WEEKENDS = True

    # Calculates other holidays based on easter sunday
    HOLIDAYS_FOR_EASTER = (0, -2, 1, 39, 50, 60)

    # ######## Logging ##########

    # A sample logging configuration.
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": True,
        "root": {
            "level": "WARNING",
            "handlers": [],
        },
        "filters": {
            "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}
        },
        "formatters": {
            "verbose": {
                "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
            },
        },
        "handlers": {
            "mail_admins": {
                "level": "ERROR",
                "filters": ["require_debug_false"],
                "class": "django.utils.log.AdminEmailHandler",
            },
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
            },
        },
        "loggers": {
            "froide": {
                "handlers": ["console"],
                "propagate": True,
                "level": "DEBUG",
            },
            "django.request": {
                "handlers": ["mail_admins"],
                "level": "ERROR",
                "propagate": True,
            },
            "django.db.backends": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    # ######## Security ###########

    CSRF_COOKIE_SECURE = False
    CSRF_FAILURE_VIEW = values.Value("froide.account.views.csrf_failure")

    # Change this
    # ALLOWED_HOSTS = ()
    ALLOWED_REDIRECT_HOSTS = ()

    SESSION_COOKIE_AGE = values.IntegerValue(3628800)  # six weeks
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False

    CSRF_COOKIE_SAMESITE = None
    SESSION_COOKIE_SAMESITE = None

    # ######## FilingCabinet Document ####

    # FILINGCABINET_DOCUMENT_MODEL = 'document.Document'
    # FILINGCABINET_DOCUMENTCOLLECTION_MODEL = 'document.DocumentCollection'

    FILINGCABINET_DOCUMENT_MODEL = "document.Document"
    FILINGCABINET_DOCUMENTCOLLECTION_MODEL = "document.DocumentCollection"
    FILINGCABINET_MEDIA_PUBLIC_PREFIX = "docs"
    FILINGCABINET_MEDIA_PRIVATE_PREFIX = "docs-private"

    # ######## Celery #############

    CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

    # Attention: The following schedule will be synchronized to the database
    CELERY_BEAT_SCHEDULE = {
        "fetch-mail": {
            "task": "froide.foirequest.tasks.fetch_mail",
            "schedule": crontab(),
        },
        "check_mail_log": {
            "task": "froide.helper.tasks.check_mail_log",
            "schedule": crontab(),
        },
        "detect-asleep": {
            "task": "froide.foirequest.tasks.detect_asleep",
            "schedule": crontab(hour=0, minute=0),
        },
        "detect-overdue": {
            "task": "froide.foirequest.tasks.detect_overdue",
            "schedule": crontab(hour=0, minute=0),
        },
        "batch-update-foirequest": {
            "task": "froide.foirequest.tasks.batch_update_requester_task",
            "schedule": crontab(hour=0, minute=1),
        },
        "batch-update-followers": {
            "task": "froide.follow.tasks.batch_update",
            "schedule": crontab(hour=0, minute=1),
        },
        "classification-reminder": {
            "task": "froide.foirequest.tasks.classification_reminder",
            "schedule": crontab(hour=7, minute=0, day_of_week=6),
        },
        "bounce-checker": {
            "task": "froide.bounce.tasks.check_bounces",
            "schedule": crontab(hour=3, minute=0),
        },
        "account-maintenance": {
            "task": "froide.account.tasks.account_maintenance_task",
            "schedule": crontab(hour=4, minute=0),
        },
        "upload-maintenance": {
            "task": "froide.upload.tasks.remove_expired_uploads",
            "schedule": crontab(hour=3, minute=30),
        },
    }

    CELERY_TASK_ALWAYS_EAGER = values.BooleanValue(True)

    CELERY_TASK_ROUTES = {
        "froide.foirequest.tasks.fetch_mail": {"queue": "emailfetch"},
        "froide.foirequest.tasks.process_mail": {"queue": "email"},
        "djcelery_email_send_multiple": {"queue": "emailsend"},
        "froide.helper.tasks.search_*": {"queue": "searchindex"},
        "froide.foirequest.tasks.redact_attachment_task": {"queue": "redact"},
        "froide.foirequest.tasks.ocr_pdf_task": {"queue": "ocr"},
        "filingcabinet.tasks.*": {"queue": "document"},
        "froide.foirequest.tasks.convert_images_to_pdf_task": {"queue": "convert"},
        "froide.foirequest.tasks.convert_attachment_task": {"queue": "convert_office"},
    }
    CELERY_TIMEZONE = "UTC"
    # We need to serialize email data as binary
    # which doesn't work well in JSON
    CELERY_TASK_SERIALIZER = "pickle"
    CELERY_RESULT_SERIALIZER = "pickle"
    CELERY_ACCEPT_CONTENT = ["pickle"]

    CELERY_EMAIL_TASK_CONFIG = {"queue": "emailsend"}
    CELERY_EMAIL_BACKEND = "froide.foirequest.smtp.EmailBackend"
    EMAIL_BULK_QUEUE = "emailsend_bulk"

    # ######## Search ###########

    ELASTICSEARCH_INDEX_PREFIX = "froide"
    ELASTICSEARCH_HOST = values.Value("localhost")
    ELASTICSEARCH_DSL = {
        "default": {"hosts": "http://%s:9200" % ELASTICSEARCH_HOST},
    }
    ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = (
        "django_elasticsearch_dsl.signals.RealTimeSignalProcessor"
    )

    # ######### API #########

    # Do not include xml by default, so lxml doesn't need to be present
    TASTYPIE_DEFAULT_FORMATS = ["json"]

    OAUTH2_PROVIDER = {
        "SCOPES": {
            "read:user": _("Access to user status"),
            "read:profile": _("Read user profile information"),
            "read:email": _("Read user email"),
            "read:request": _("Read your (private) requests"),
            "make:request": _("Make requests on your behalf"),
            "follow:request": _("Follow/Unfollow requests"),
            "read:document": _("Read your (private) documents"),
        }
    }
    OAUTH2_PROVIDER_APPLICATION_MODEL = "account.Application"

    LOGIN_URL = "account-login"

    REST_FRAMEWORK = {
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
            "rest_framework.authentication.SessionAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": (
            "rest_framework.permissions.IsAuthenticatedOrReadOnly",
        ),
        "DEFAULT_PAGINATION_CLASS": "froide.helper.api_utils.CustomLimitOffsetPagination",
        "PAGE_SIZE": 50,
        "DEFAULT_FILTER_BACKENDS": (
            "django_filters.rest_framework.DjangoFilterBackend",
        ),
        "DEFAULT_RENDERER_CLASSES": (
            "rest_framework.renderers.JSONRenderer",
            "froide.helper.api_renderers.CustomPaginatedCSVRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        ),
        "DEFAULT_SCHEMA_CLASSES": ("drf_spectacular.openapi.AutoSchema",),
    }

    # ######### Froide settings ########

    FROIDE_CONFIG = dict(
        spam_protection=True,
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
        read_receipt=False,
        delivery_receipt=False,
        dsn=False,
        target_countries=None,
        suspicious_asn_provider_list=None,
        request_throttle=None,  # Set to [(15, 7 * 24 * 60 * 60),] for 15 requests in 7 days
        message_throttle=[
            (2, 5 * 60),  # X messages in X seconds
            (6, 6 * 60 * 60),
            (8, 24 * 60 * 60),
        ],
        allow_pseudonym=False,
        doc_conversion_binary=None,  # replace with libreoffice instance
        doc_conversion_call_func=None,  # see settings_test for use
        content_urls={
            "terms": "/terms/",
            "privary": "/privacy/",
            "about": "/about/",
            "help": "/help/",
            "throttled": "/help/",
        },
        moderation_triggers=[
            {
                "name": "nonfoi",
                "label": _("Non-FOI"),
                "icon": "fa-ban",
                "applied_if_actions_applied": [0],
                "actions": [
                    ("froide.foirequest.moderation.MarkNonFOI",),
                    (
                        "froide.foirequest.moderation.SendUserEmail",
                        "foirequest/emails/non_foi",
                    ),
                ],
            },
            {
                "name": "depublish",
                "label": _("Give warning"),
                "icon": "fa-minus-circle",
                "actions": [
                    ("froide.foirequest.moderation.Depublish",),
                ],
            },
        ],
        message_handlers={
            "email": "froide.foirequest.message_handlers.EmailMessageHandler"
        },
        recipient_blocklist_regex=None,
        max_attachment_size=1024 * 1024 * 10,  # 10 MB
        bounce_enabled=False,
        bounce_max_age=60 * 60 * 24 * 14,  # 14 days
        bounce_format="bounce+{token}@example.com",
        unsubscribe_enabled=False,
        unsubscribe_format="unsub+{token}@example.com",
        auto_reply_subject_regex=rec("^(Auto-?Reply|Out of office)"),
        auto_reply_email_regex=rec("^auto(reply|responder)@"),
        hide_content_funcs=[],
        filter_georegion_kinds=[
            "state",
            "admin_district",
            "district",
            "admin_cooperation",
            "municipality",
            "borought",
        ],
        non_meaningful_subject_regex=[
            r"^(foi[- ])?request$",
            r"^documents?$",
            r"^information$",
        ],
        address_regex=None,
    )

    TESSERACT_DATA_PATH = values.Value("/usr/local/share/tessdata")
    # allow override of settings.LANGUAGE_CODE for Tesseract
    TESSERACT_LANGUAGE = None

    # ###### Email ##############

    # Django settings

    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    EMAIL_SUBJECT_PREFIX = values.Value("[Froide] ")
    SERVER_EMAIL = values.Value("error@example.com")
    DEFAULT_FROM_EMAIL = values.Value("info@example.com")

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
    FOI_EMAIL_PORT = values.IntegerValue(587)
    FOI_EMAIL_USE_TLS = values.BooleanValue(True)

    # The FoI Mail can use a different account
    FOI_EMAIL_DOMAIN = values.Value("example.com")
    # For generating email Message-Id
    FOI_MAIL_SERVER_HOST = values.Value("mail.example.com")

    FOI_EMAIL_TEMPLATE = None
    # Example:
    # FOI_EMAIL_TEMPLATE = lambda user_name, secret: "{username}.{secret}@{domain}" % (user_name, secret, FOI_EMAIL_DOMAIN)

    # Is the message you can send from fixed
    # or can you send from any address you like?
    FOI_EMAIL_FIXED_FROM_ADDRESS = values.BooleanValue(True)

    BOUNCE_EMAIL_HOST_IMAP = values.Value("")
    BOUNCE_EMAIL_PORT_IMAP = values.Value(143)
    BOUNCE_EMAIL_ACCOUNT_NAME = values.Value("")
    BOUNCE_EMAIL_ACCOUNT_PASSWORD = values.Value("")
    BOUNCE_EMAIL_USE_SSL = values.Value(False)

    UNSUBSCRIBE_EMAIL_HOST_IMAP = values.Value("")
    UNSUBSCRIBE_EMAIL_PORT_IMAP = values.Value(143)
    UNSUBSCRIBE_EMAIL_ACCOUNT_NAME = values.Value("")
    UNSUBSCRIBE_EMAIL_ACCOUNT_PASSWORD = values.Value("")
    UNSUBSCRIBE_EMAIL_USE_SSL = values.Value(False)

    SPECTACULAR_SETTINGS = {
        "SWAGGER_UI_DIST": "SIDECAR",
        "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
        "REDOC_DIST": "SIDECAR",
    }


class Dev(Base):
    pass


class TestBase(Base):
    DEBUG = False

    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]

    ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = (
        "django_elasticsearch_dsl.signals.BaseSignalProcessor"
    )

    @property
    def TEMPLATES(self):
        TEMP = super().TEMPLATES
        TEMP[0]["OPTIONS"]["debug"] = True
        return TEMP

    def _fake_convert_pdf(self, infile, outpath):
        _, filename = os.path.split(infile)
        name, ext = filename.rsplit(".", 1)
        output = os.path.join(outpath, "%s.pdf" % name)
        args = ["cp", infile, output]
        return args, output

    @property
    def FROIDE_CONFIG(self):
        config = dict(super().FROIDE_CONFIG)
        config.update(
            dict(
                spam_protection=False,
                doc_conversion_call_func=self._fake_convert_pdf,
                default_law=10000,
                greetings=[
                    rec(r"Dear ((?:Mr\.?|Ms\.?) .*),?"),
                    rec(r"Sehr geehrter? ((Herr|Frau) .*),?"),
                ],
                closings=[rec(r"Sincerely yours,?"), rec(r"Mit freundlichen Grüßen")],
                public_body_officials_public=False,
            )
        )
        return config

    @property
    def MEDIA_ROOT(self):
        return super().PROJECT_ROOT / "tests" / "testdata"

    ALLOWED_HOSTS = ("localhost", "testserver")

    ELASTICSEARCH_INDEX_PREFIX = "froide_test"

    MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

    TEST_SELENIUM_DRIVER = values.Value("chrome_headless")

    SECRET_URLS = values.DictValue(
        {
            "admin": "admin",
        }
    )

    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "info@example.com"

    FOI_EMAIL_DOMAIN = "fragdenstaat.de"

    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

    MIDDLEWARE = [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.locale.LocaleMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
    ]
    FROIDE_CSRF_MIDDLEWARE = "django.middleware.csrf.CsrfViewMiddleware"


class Test(TestBase):
    pass


class German(object):
    LANGUAGE_CODE = "de"
    LANGUAGES = (("de", _("German")),)

    DATE_FORMAT = "d. F Y"
    SHORT_DATE_FORMAT = "d.m.Y"
    DATE_INPUT_FORMATS = ("%d.%m.%Y",)
    DATETIME_FORMAT = "j. F Y, H:i"
    SHORT_DATETIME_FORMAT = "d.m.Y H:i"
    DATETIME_INPUT_FORMATS = ("%d.%m.%Y %H:%M",)
    TIME_FORMAT = "H:i"
    TIME_INPUT_FORMATS = (
        "%H:%M:%S",
        "%H:%M",
    )
    SLUGIFY_REPLACEMENTS = (
        ("Ä", "Ae"),
        ("ä", "ae"),
        ("Ö", "Oe"),
        ("ö", "oe"),
        ("Ü", "Ue"),
        ("ü", "ue"),
        ("ß", "ss"),
    )

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
        german_config = dict(super().FROIDE_CONFIG)
        german_config.update(
            {
                "payment_possible": True,
                "currency": "Euro",
                "public_body_boosts": {
                    "Oberste Bundesbeh\xf6rde": 1.9,
                    "Obere Bundesbeh\xf6rde": 1.1,
                    "Ministerium": 1.8,
                    "Senatsverwaltung": 1.8,
                    "Kommunalverwaltung": 1.7,
                    "Andere": 0.8,
                },
                "autocomplete_body_boosts": {"Bund": 1.5},
                "greetings": [
                    rec(r"Sehr geehrt(er? (?:Herr|Frau)(?: ?Dr\.?)?(?: ?Prof\.?)? .*)")
                ],
                "redact_salutation": r"(?:er?\s+)?(?:Herr|Frau)",
                "closings": [
                    rec(r"Mit freundlichen Gr\xfc\xdfen,?"),
                    rec(r"Mit den besten Grüßen,?"),
                ],
            }
        )
        return german_config


class Production(Base):
    DEBUG = False

    @property
    def TEMPLATES(self):
        TEMP = super().TEMPLATES
        TEMP[0]["OPTIONS"]["debug"] = False
        return TEMP

    ALLOWED_HOSTS = values.TupleValue(("example.com",))
    CELERY_TASK_ALWAYS_EAGER = values.BooleanValue(False)
    STATICFILES_STORAGE = (
        "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    )


class SSLSite(object):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTOCOL", "https")
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    LANGUAGE_COOKIE_SECURE = True


def os_env(name):
    return os.environ.get(name)


try:
    from .local_settings import *  # noqa
except ImportError:
    pass
