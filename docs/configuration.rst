=============
Configuration
=============

Froide can be configured in many ways to reflect the needs of your local FoI portal.

The `custom_settings.py.example` file that comes with froide has all the settings from the `settings.py` file but they are commented out. You can copy this file to `custom_settings.py`

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

**search_engine_query**
  *string* You can give a URL with string formatting placeholders `query` and `domain` in them that will be presented to the user as the URL for web searches. The default is a Google search.


Greeting Regexes
----------------

To detect names and beginning and endings of letters the standard
settings define a list of common English letter greeting and closing
regexes that also find the name::

    import re
    rec = re.compile
    # define your greetings and closing regexes

    FROIDE_CONFIG.update(
        dict(
            greetings=[rec(u"Dear (?:Mr\.?|Ms\.? .*?)")],
            closings=[rec(u"Sincerely yours,?")]
        )
    )

You should replace this with a list of the most common expressions in
your language.

Index Boosting of Public Bodies
-------------------------------

Some Public Bodies are more important and should appear first in
searches (if their name and description match the search terms). You can
provide a mapping of public body classifications (e.g. ministry,
council etc.) to their search boost factor via the `public_body_boosts`
key in the `FROIDE_CONFIG` setting::

    # boost public bodies by their classification
    FROIDE_CONFIG.update(
        'public_body_boosts': {
            u"Ministry": 1.9,
            u"Council": 0.8
        }
    })


Public Body E-Mail Dry-run
--------------------------

You can set your site up and test it out in a production environment
while sending public body emails not to the public bodies but to
another mail server. Use the following settings::

    FROIDE_CONFIG.update(
        dict(
            dryrun=False,
            dryrun_domain="testmail.example.com"
        )
    )

This converts public body email addresses from

    public-body@example.com

to

    public-body+example.com@testmail.example.com

right before the mail is
sent out (the changed address is not stored). This allows for some
testing of sending and receiving mails to and from public bodies wihtout spamming them.


Settings for Sending E-Mail
---------------------------

You must adapt the standard Django parameters for sending email.
Configure the backend depending on your environment (development vs.
production)::

    # development/testing environment:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    # production environment:
    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'

Define the standard Django SMTP parameters for sending regular email notifications (not FoI request emails to public bodies)::

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


Some more settings
------------------

Configure the name, default domain URL and default email (without trailing slash) of your site with the following settings::

    SITE_NAME = 'FroIde'
    SITE_URL = 'http://localhost:8000'
    SITE_EMAIL = 'info@example.com'

More suggestions of settings you can change can be found in the `custom_settings.py.example` file that comes with froide.


Securing your site
------------------

It may be a good idea to NOT use easily guessable URL paths for
specific parts of the site, specifically the admin. To make these
parts configurable by `local_settings` you can use the following
setting::

    SECRET_URLS = {
        "admin": "my-secret-admin"
    }

It's also recommended to protect the admin further via HTTP
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

Make sure that your frontend server transports the information that HTTPS is used to the web server.