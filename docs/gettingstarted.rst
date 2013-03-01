===============
Getting Started
===============

This is a guide that will get you started with Froide in no time. Some
more advanced features are discussed at the end.


Set up the development environment
----------------------------------

You should be using a Python virtual environment.
Setup a virtual environment for development with `virtualenv`like so::

    virtualenv --no-site-packages ~/pyenv
    . ~/pyenv/bin/activate

Get the source code with Git from the GitHub repository::

    git clone git://github.com/stefanw/froide.git
    cd froide

Install the requirements inside the virtual env with `pip`::

    pip install -r requirements.txt

The dependency installation may take a couple of minutes, but after that everything is in place.

Sync and migrate and *do NOT* create a superuser just yet::

    python manage.py syncdb --noinput --migrate

Now you can already start the web server::

    python manage.py runserver

Visit `http://localhost:8000 <http://localhost:8000>`_ and there is your running Froide instance!

You can quit the server (Ctrl+C) and create a superuser account::

    python manage.py createsuperuser


Add basic database objects
--------------------------

Run the web server again and login to the admin interface at `http://localhost:8000/admin/ <http://localhost:8000/admin/>`_ with the credentials of your superuser.

The first thing you should do is create a jurisdiction. Click on "Jurisdiction" in the "Publicbody" section and then on "Add Jurisdiction".
Name your jurisdiction however you want (e.g. Federal). If you only ever intend to have one, the name will not even show up. Click "Save" to continue.

Go back into the public body section and add an FOI law. Give it a name (e.g. Freedom of Information Act) and choose a jurisdiction. There are many more things that can be configured, but you can leave them for now.

Now you can add your first public body by going back to the public body section and clicking on "Add" next to "Public Bodies". Give it a name (e.g. Ministry of the Interior).
Click on the little plus-sign next to topic to add a topic for this public body. The classification is to distinguish different areas of government (e.g. "Ministry", "Council").
If you want to make a request to this public body, it needs to have an email address.
Select your previously created jurisdiction and FOI law and save.

You should also fill out your user details like your name in the user section of the admin.

Now you are ready to make your first request. Go back to the front page and give it a go. You can also find out more about the :doc:`admin`.


Custom configuration
--------------------

By default the Django Web server uses the `settings.py` file in the froide directory (the `froide.settings` Python module). This will be fine for your first experiments but if you want to customize your froide instance you will want your own settings file.

Go into the froide directory and copy the `custom_settings.py.example` to `custom_settings.py`::

    cd froide
    cp custom_settings.py.example custom_settings.py

Now you can customize that settings file to your liking. Note that it imports the original `settings.py` at the top, so you only have to change the values you need to change.

In order for Django to start your web server with these new settings you either have to set the environment variable `DJANGO_SETTINGS_MODULE` or give the settings module as a command line argument.

Either type::

    export DJANGO_SETTINGS_MODULE=froide.custom_settings
    python manage.py runserver

The environment variable will be set for this shell session. If you open a new shell, you have to export the settings again.
Or::

    python manage.py runserver --settings=froide.custom_settings

Since it can be annoying to type this (or to remember to export the environment variable), you can create a shortcut shell script, create an alias, put an export in your virtualenv's `activate` file or use `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/>`_ and put the export in your `postactivate` hook.



Search with Haystack
--------------------

In order to get a real search engine running you need to override the `HAYSTACK_CONNECTIONS` setting with the details of your search engine. Find out `how to configure your search engine at the Haystack Docs <http://django-haystack.readthedocs.org/en/latest/tutorial.html#modify-your-settings-py>`_.

An example configuration for solr would look like this::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://127.0.0.1:8983/solr/froide'
        }
    }


Background Tasks with Celery
----------------------------

From the standard settings file everything is already setup for background tasks except that they are not running in the background.

You need to change the `CELERY_ALWAYS_EAGER` setting to `False` in your custom settings::

    CELERY_ALWAYS_EAGER = False

You need a broker for Celery. Find out more at the `Celery Docs <http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html#choosing-a-broker>`_.

We recommend `RabbitMQ <http://www.rabbitmq.com/>`_ as broker. Install it and then start it in a different terminal like this::

    rabbitmq-server

After you started the broker open yet another terminal, activate your virtual environment and run the celery worker like this::

    python manage.py celeryd -l INFO -B

Now your server will send background tasks to Celery. Lots of common tasks are designed as background tasks so that an ongoing HTTP request can send a response more quickly. The following things are designed as background tasks:

- Search Indexing: Updates to database objects are indexed in the background
- Email Sending: When an action triggers an email, it's sent in the background
- Denormalized Counts on database objects

Celery also takes the role of `cron` and handles periodic tasks. You should set up periodic tasks in the admin under "Djcelery - Periodic tasks". Here is a recommended configuration:

- Fetch Mail: every minute
- Detect Overdue at Midnight: 0 0 * * * (m/h/d/dM/MY)
- Batch Update Followers every 24 hours: 0 0 * * * (m/h/d/dM/MY)
- Remind users to classify there requests: 0 7 6 * * (m/h/d/dM/MY)
