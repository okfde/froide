=================
Heroku Deployment
=================

The following guide will let you deploy an instance of Froide on `Heroku <http://heroku.com>`_ together with `Postmark <https://postmarkapp.com/>`_ for email sending/receiving and S3 for file storage and static file serving.
Heroku and Postmark are free with limited capacity, S3 will cost you a tiny bit of money. You can also use any other file storage/serving service that is supported by `Django Storages <http://django-storages.readthedocs.org/en/latest/>`_.


Install your Froide instance on Heroku
--------------------------------------

1. Install the `heroku toolbelt <https://toolbelt.heroku.com/>`_.

2. Create a virtualenv::

    # Install virtualenv
    curl -O https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.1.tar.gz
    tar -xvf virtualenv-1.10.1.tar.gz
    python virtualenv-1.10.1/virtualenv.py froidetheme
    # Activate it
    source froidetheme/bin/activate

3. Download and install Froide Theme::

    git clone https://github.com/okfn/froide-theme.git
    cd froide-theme
    pip install -r requirements.txt -e .


4. Register at Heroku and create a new app through the `Heroku Dashboard <https://dashboard.heroku.com/apps>`_.

5. Add the Heroku remote to the repository and push::

    git remote add heroku git@heroku.com:<your-heroku-name>.git
    git push heroku master

6. Set some configuration, change the ``DJANGO_SECRET_KEY`` value to something secret and give the correct Heroku App URL in ``DJANGO_SITE_URL``::

    heroku config:set DJANGO_SETTINGS_MODULE=froide_theme.settings DJANGO_CONFIGURATION=ThemeHerokuPostmark DJANGO_SECRET_KEY="Your RANDOM secret key" DJANGO_SITE_URL="http://<your-heroku-name>.herokuapp.com"

7. Initialize the Heroku database by running::

    heroku run python manage.py syncdb --noinput --migrate

Congratulations, you can already access your Froide instance at::

     http://<your-heroku-name>.herokuapp.com/

You can continue you further here or read up on post-installation setup in :ref:`add-basic-database-objects`.


Set up Email Sending and receiving
----------------------------------

You will need access to a domain and its DNS settings.


1. Add the `Postmark Add-On to your Heroku App <https://addons.heroku.com/postmark#10k>`_.

2. Run the following in your terminal, which will open a web page::

    heroku addons:open postmark

3. Click on "Details" on your Server, go to settings and set the bounce URLs::

    # Bounce Hook
    http://<your-heroku-name>.herokuapp.com/postmark/postmark_bounce/
    # Inbound  Hook
    http://<your-heroku-name>.herokuapp.com/postmark/postmark_inbound/

4. Setup the MX records for your domain and make the API call like `described in this article <http://developer.postmarkapp.com/developer-inbound-mx.html>`_. The "Token" mentioned is your API key that you can find on the postmark page under Credentials.

5. For setting up sender signatures you should allow some hours to pass so that MX records are recognized. In Postmark click on "Sender Signatures" and add a new signature for your domain. You should setup two signatures: one for regular notification mails (e.g. mail@inbound.example.com) and the other for sending out requests (request@inbound.example.com). You should also setup the DKIM and SPF records for you domain and verify them.

   Since the confirmation mails for sending signatures should go to Postmark, check the "Inbound" tab of your "Activity" page of your Postmark account and use the confirmation link in the incoming email. This can take some time because of DNS propagation. You may have to resend the confirmation emails.

6. Set the following config values in Heroku::

    heroku config:set DJANGO_DEFAULT_FROM_EMAIL=mail@inbound.example.com
    heroku config:set DJANGO_FOI_EMAIL_DOMAIN=inbound.example.com
    # The following should conform with your request mail name
    # followed by a + sign like this:
    heroku config:set DJANGO_FOI_EMAIL_TEMPLATE="request+{secret}@{domain}"
    heroku config:set DJANGO_SERVER_EMAIL=mail@inbound.example.com
    heroku config:set DJANGO_SITE_EMAIL=mail@inbound.example.com


Enable mail attachment storage and faster static file serving
-------------------------------------------------------------

1. Set up an Amazon Web Services account with S3
2. Create a bucket and an access key
3. Set the values as Heroku config::

    heroku config:set DJANGO_AWS_ACCESS_KEY_ID=<YOUR_ACCESS_KEY>
    heroku config:set DJANGO_AWS_SECRET_ACCESS_KEY=<YOUR_SECRET>
    heroku config:set DJANGO_AWS_STORAGE_BUCKET_NAME=<YOUR BUCKET NAME>
    # Must end with a /
    heroku config:set DJANGO_STATIC_URL=http://your-bucket-name.s3.amazonaws.com/


Worker Threads
--------------

To keep the cost for initial setup minimal, there are no worker processes.
However, you can setup a queueing add-on (or, though not recommended, use database as queue) and then put a worker processe in your Procfile to run ``celery worker`` and another for ``celery beat``.

For regular scheduling tasks like reminders, this is the way to go.