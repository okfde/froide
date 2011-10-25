===============
Getting Started
===============

This is a guide that will get you started with Froide in no time. Some
more advanced features are discussed at the end.


Set up the development environment
----------------------------------

You should be using `virtualenv` and it is suggested you
also use `virtualenvwrapper`. Setup a virtual environment for development like so::

    mkvirtualenv --no-site-packages froide

Get the source code with Git from the official GitHub repository or from
your fork::

    git clone git://github.com/stefanw/froide.git
    cd froide

Install the requirements inside the virtual env with `pip`::

    which pip
    <should display your virtual env pip>
    pip install -r requirements.txt

If only your global `pip` is available, run `easy_install pip`. The dependency installation takes a couple of seconds, but after that everything is in place.

Copy `local_settings.py.example` to `local_settings.py`::

    cd froide
    cp local_settings.py.example local_settings.py

The development environment uses SQLite. You can change that in `local_settings.py`, if you want, but you don't have to.
Sync and migrate and *do NOT* create a superuser just yet::

    python manage.py syncdb --noinput --migrate

Now you can create a superuser account::

    python manage.py createsuperuser

That's it for a setup that basically works. Run this::

    python manage.py runserver

and go to `http://localhost:8000 <http://localhost:8000>`_. You should
be greeted by a working Froide installation. It doesn't have any data
inside, but you can change that by going to `http://localhost:8000/admin/ <http://localhost:8000/admin/>`_ and logging in with your superuser account.

For more information on the different models you find in the admin visit :doc:`models`.

Run tests
---------

Froide has a test suite. Copy `test_settings.py.example` to `test_settings.py`. `test_settings.py` does not import your `local_settings.py` changes.

You can then run the shell script for tests::

    sh runtests.sh

This also does timing and a test coverage analysis that you can then
find at `htmlcov/index.html`.
Note some tests will not work without a search engine like solr running.


Search with Haystack and Solr
-----------------------------


Background Processing with Celery
---------------------------------


