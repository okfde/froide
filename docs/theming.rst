==============
Theming Froide
==============

If want to customize the look of your own Froide instance or add other pages to it, you can create a theme and install it in your Froide instance.

See the `FragDenStaat.de Theme <https://github.com/okfde/fragdenstaat_de>`_ as an example.

Basics
------

A theme is normal Python Package and Django App. The app's templates, static files and urls will be found first be Froide and therefore override the normal files of Froide.

URLs
----

You can add custom URLs to your Froide instance by placing an `urls.py` file in the app.
The url patterns will be hooked to the root of the Froide URLs and are the first to be considered for routing.
An example might look like this::

  from django.conf.urls import patterns, url
  from django.http import HttpResponseRedirect

  urlpatterns = patterns('fragdenstaat_de.views',
      url(r'^nordrhein-westfalen/', lambda request: HttpResponseRedirect('/nrw/'),
          name="jurisdiction-nrw-redirect")
  )

This is simply a custom redirect for a jurisdiction URL but you can also hook up your own views.

Static files
------------

You can override the serving of existing static files by placing a `static` folder in your theme app.
If you put a file like `img/logo.png` in the `static` folder of your theme, Froide will serve the theme logo
instead of the standard Froide logo. You can also override and add CSS and JavaScript files like this.

Templates
---------

Most likely you want to change some parts of the site, but keep most of it the same.
The Django template language allows you to extend base template and override blocks. However, if you override the base template you have to copy over all blocks. To circumvent that Froide comes with the template tag `overextend`.
It allows to override only the specific blocks in templates and keeps the other blocks the same.

An example for the `base.html` template could look like this::

  {% overextends "base.html" %}
  {% load i18n %}

  {% block footer_description %}
  <p>
    {% blocktrans with url=about_url %}Froide is a free and Open Source Project by <a href="http://www.okfn.org">the Open Knowledge Foundation</a>.{% endblocktrans %}
  </p>
  {% endblock %}

This will only override the footer description of the `base.html` template.

Have a look at the Froide templates to find block you can override. If you need to override a specific part that is not enclosed in a block tag yet, open a pull request. More blocks are always welcome.
