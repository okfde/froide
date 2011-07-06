=============
Configuration
=============

Froide can be configured in many ways to reflect the needs of your local FoI portal.

All configuration is kept in the Django `settings.py` file. Individual settings can be overwritten by placing a `local_settings.py` file on the Python path (e.g. in the same directory) and redefining the configuration key in there.

Froide Configuration
--------------------

There is a dictionary called `FROIDE_CONFIG` that acts as a namespace for some other configurations. The following keys must be configured:


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


rec = re.compile
# define your greetings and closing regexes
POSSIBLE_GREETINGS = [rec(u"Sehr geehrt(er? (?:Herr|Frau) .*?)")]
POSSIBLE_CLOSINGS = [rec(u"Mit freundlichen Grüßen,?")]


# boost public bodies by their classification
FROIDE_PUBLIC_BODY_BOOSTS = {
    u"Ministry": 1.9,
    u"Council": 0.8
}

# dev use:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_HOST = "smtp.example.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = "mail@foi.example.com"
EMAIL_HOST_PASSWORD = "password"
EMAIL_USE_TLS = True

FOI_EMAIL_DOMAIN = "foi.example.com"
FOI_EMAIL_PORT_IMAP = 993
FOI_EMAIL_HOST_IMAP = "imap.example.com"
FOI_EMAIL_ACCOUNT_NAME = "foirelay@foi.example.com"
FOI_EMAIL_ACCOUNT_PASSWORD = "password"

FOI_EMAIL_FIXED_FROM_ADDRESS = True
FOI_EMAIL_HOST_USER = FOI_EMAIL_ACCOUNT_NAME
FOI_EMAIL_HOST_PASSWORD = FOI_EMAIL_ACCOUNT_PASSWORD
FOI_EMAIL_HOST = "smtp.example.com"
FOI_EMAIL_PORT = 537
FOI_EMAIL_USE_TLS = True

