=============
Configuration
=============

Froide can be configured in many ways to reflect the needs of your local FoI portal.

All configuration is kept in the Django `settings.py` file. Individual settings can be overwritten by placing a `local_settings.py` file on the Python path (e.g. in the same directory) and redefining the configuration key in there.

Froide Configuration
--------------------

There is a dictionary called `FROIDE_CONFIG` inside settings.py that acts as a namespace for some other configurations. These settings are also available in the template via the name `froide` through the context processor `froide.helper.context_processors.froide`.

The following keys in that dictionary must be present:


**create_new_publicbody**
  *boolean* Are users allowed to create new public bodies when making a request by filling in some details?
  Newly created public bodies must be approved by an administrator before the request is sent.

**publicbody_empty**
  *boolean* Can users leave the public body empty on a request, so other users can suggest an appropriate public body later?

**users_can_hide_web**
  *boolean* Can users hide their name on the portal? Their name will always be sent with the request, but may not appear on the website.

**public_body_officials_public**
  *boolean* Are the names of responding public body officials public and visible on the Web?

**public_body_officials_email_public**
  *boolean* Are the email addresses of public body officials public and visible on the Web?

**currency**
  *string* The currency in which payments (if at all) occur

**default_law**
  *integer* The id of the Freedom of Information law in the database
  that is used by default (e.g. 1)


Greeting Regexes
----------------

To detect names and beginning and endings of letters the standard
settings define a list of common English letter greeting and closing
regexes that also find the name::

    import re
    rec = re.compile
    # define your greetings and closing regexes
    POSSIBLE_GREETINGS = [rec(u"Dear (?:Mr\.?|Ms\.? .*?)")]
    POSSIE_CLOSINGS = [rec(u"Sincerely yours,?")]

You should replace this with a list of the most common expressions in
your language.

Index Boosting of Public Bodies
-------------------------------

Some Public Bodies are more important and should appear first in
searches (if there name and description match the search terms). You can
provide a mapping of public body classifications (e.g. ministry,
council etc.) to their search boost factor via the `FROIDE_PUBLIC_BODY_BOOSTS` setting::

    # boost public bodies by their classification
    FROIDE_PUBLIC_BODY_BOOSTS = {
        u"Ministry": 1.9,
        u"Council": 0.8
    }



Settings for Sending E-Mail
---------------------------

You must adapt the standard Django parameters for sending email.
Configure the backend depending on your environment (development vs.
production)::

    # development environment:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    # production environment:
    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'

Define the standard Django SMTP parameters for sending regular (not FoI-Email to public bodies)::

    EMAIL_HOST = "smtp.example.com"
    EMAIL_PORT = 587
    EMAIL_HOST_USER = "mail@foi.example.com"
    EMAIL_HOST_PASSWORD = "password"
    EMAIL_USE_TLS = True

Also define the parameters for sending FoI-Mails to public bodies.
They might be different because they can either be sent from a fixed
address and with a special `Reply-To` field or directly from a special
address::

    # Sends mail from a fixed from address with Reply-To field
    FOI_EMAIL_FIXED_FROM_ADDRESS = True
    FOI_EMAIL_HOST_USER = "foirelay@foi.example.com"
    FOI_EMAIL_HOST_PASSWORD = "password"
    FOI_EMAIL_HOST = "smtp.example.com"
    FOI_EMAIL_PORT = 537
    FOI_EMAIL_USE_TLS = True

Finally give the IMAP settings of the account that receives all FoI
email. This account is polled regularly and the messages are processed
and displayed on the website if their `To` field matches::

    FOI_EMAIL_DOMAIN = "foi.example.com"
    FOI_EMAIL_PORT_IMAP = 993
    FOI_EMAIL_HOST_IMAP = "imap.example.com"
    FOI_EMAIL_ACCOUNT_NAME = "foirelay@foi.example.com"
    FOI_EMAIL_ACCOUNT_PASSWORD = "password"


Public Body E-Mail Dry-run
--------------------------

You can set your site up and test it out in a production environment
while sending public body e-mails not to the public bodies but to
another mail server. Use the following settings::

    FROIDE_DRYRUN = True
    FROIDE_DRYRUN_DOMAIN = "mymail.example.com"

This converts public body email addresses from

    public-body@example.com

to

    public-body+example.com@mymail.example.com

right before the mail is
send out (the changed address is not stored). This allows for some
testing of sending and receiving mails to and from public bodies wihtout spamming them.

Setting Up Search with Solr
---------------------------

Froide uses `django-haystack` to interface with a search. Solr is
recommended, but thanks to `django-haystack` you can use something
else as well.

Haystack configuration for solr works like so::

    HAYSTACK_SITECONF = 'froide.search_sites'
    HAYSTACK_SEARCH_ENGINE = 'solr'
    HAYSTACK_SOLR_URL = 'http://127.0.0.1:8983/solr'

For details, please refer to the Haystack Documentation.

Setting Up Background Processing with Celery
--------------------------------------------

The following part in `settings.py` does the configuration of Celery.
Overwrite the `CELERY*` values with your own in `local_settings.py`::

    import djcelery
    djcelery.setup_loader()

    CELERY_IMPORTS = ("foirequest.tasks", )

    CELERY_RESULT_BACKEND = "database"
    CELERY_RESULT_DBURI = "sqlite:///dev.db"

    CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"

For details please refer to the `django-celery documentation <http://django-celery.readthedocs.org/en/latest/index.html>`_.

Some more settings
------------------

Configure the name and default domain URL (without trailing slash) of your site with the following settings::

    SITE_NAME = 'FroIde'
    SITE_URL = 'http://localhost:8000'

You can give a URL with string formatting placeholders `query` and `domain` in them that will be presented to the user as the URL for web searches via the setting `SEARCH_ENGINE_QUERY`. The default is a Google search.


Securing your site
------------------

It may be a good idea to NOT use easily guessable URL paths for
specific parts of the site, specifically the admin. To make these
parts configurable by `local_settings` you can use the following
setting::

    SECRET_URLS = {
        "admin": "my-secret-admin",
        "sentry": "my-secret-sentry"
    }

It's also recommended to protect the admin and sentry further via HTTP
auth in your production reverse proxy (e.g. nginx).

The app `djangosecure <https://github.com/carljm/django-secure/>`_ is part of Froide
and it is highly recommended to
deploy the site with SSL (`get a free SSL certificate from StartSSL <https://github.com/ioerror/duraconf/blob/master/startssl/README.markdown>`_).

Some Django settings related to security and SSL::

    CSRF_COOKIE_SECURE = True
    CSRF_FAILURE_VIEW = 'froide.account.views.csrf_failure'

    SESSION_COOKIE_AGE = 3628800 # six weeks for usability
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
