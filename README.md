Froide
======

[![Build Status](https://travis-ci.org/stefanw/froide.png?branch=master)](https://travis-ci.org/stefanw/froide)


Froide is a Freedom Of Information Portal written in Python using Django 1.5.

It is used by the German and the Austrian FOI site, but it is fully
internationalized and written in English.

Docs
----

[Read the documentation](http://readthedocs.org/docs/froide/en/latest/) including a [Getting Started Guide](http://readthedocs.org/docs/froide/en/latest/gettingstarted/).

Froide is supported by the [Open Knowledge Foundation](http://okfn.org/).

Deployments on Heroku
~~~~~~~~~~~~~~~~~~~~~

Deploying on Heroku

    # you would rename your app from myfroide to something different
    heroku create myfroide

    # have to push our heroku branch
    git push heroku 81-heroku:master

    # run relevant getting start commands
    heroku run python manage.py syncdb --noinput --migrate

#### Configuration

Setting up config vars on Heroku see <https://devcenter.heroku.com/articles/config-vars>

Specific things you'll want to tweak are (this could go in your .env file):

    SITE_NAME=...
    # Email settings - e.g. for sendgrid
    EMAIL_HOST="smtp.sendgrid.net"
    EMAIL_PORT=25

License
-------

Froide is licensed under the MIT License.

Some folders contain an attributions.txt with more information about the copyright holders in this specific folder.
