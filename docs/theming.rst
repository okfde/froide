==============
Theming Froide
==============

If want to customize the look of your own Froide instance or add other pages to it, you can create a theme and install it in your Froide instance.

See the `FragDenStaat.de Theme <https://github.com/okfde/fragdenstaat_de>`_ as a real-life example or use the `Basic Froide Theme <https://github.com/okfde/froide-theme>`_ as a starting point.

Basics
------

A theme is normal Django project with a theme app. The app's templates, static files and urls will be found first by Froide and therefore override the normal files of Froide. A hook in the root url conf allows to override or extend the site with more URLs.

URLs
----

You can add custom URLs to your Froide instance by placing an `urls.py` file in the theme app.
The url patterns will be hooked to the root of the Froide URLs and are the first to be considered for routing.
An example might look like this::

  from django.conf.urls import url
  from django.http import HttpResponseRedirect

  urlpatterns = [
      url(r'^long-custom-url/', lambda request: HttpResponseRedirect('/url/'),
          name="longurl-redirect")
  ]

This is simply a custom redirect for a URL but you can also hook up your own views.

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


Help URLs and Flatpages
-----------------------

The following standard URL names are referenced from templates: ``help-index``, ``help-about``, ``help-terms`` and ``help-privacy``.
You can create Django Flatpages for these URLs or their appropriate translations: ``/help/``, ``/help/about/``, ``/help/terms/`` and ``/help/privacy/``.

You can overwrite these URLs by their name in the root URL conf of your theme. You can also overwrite their base templates.
