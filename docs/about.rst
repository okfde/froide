=====
About
=====

Froide is a Freedom of Information portal software written in Python with Django 1.5.


Development Goals
-----------------

Froide has some development goals that are listed below. Some of them
are a continuous effort, some are achieved, on others development is
still ongoing.

- Internationalization (i18n): Keep the code fully internationalized and
  localized.
- Flexible and Configurable: Many aspects of an FoI platform depend on local customs and laws. These aspects should be either configurable via settings or easily replaceable.
- Easy to install: Keep dependencies to one language environment (Python) and use abstraction layers for backends like search, caching etc. to enable different setups.
- Maintain a test suite with a high test coverage.

Features
--------

- Froide uses many of the built-in Django features like the Admin interface to
  manage and update entities in the system, the internationalization
  system, and the user management and authentication.
- Freedom of Information Laws and Public Entities are connected through a many-to-many relationship. That allows for a Public Body to be accountable under different laws.
- A Public Body can have a parent to represent hierarchies from the real
  world. They can also be categorized into classifications (e.g. ministry, council) and topics (e.g. environment, military) which can be defined separately.
- Users can create requests without a Public Body so that others can
  suggest an appropriate recipient later.
- Requests can optionally be kept private by users and published at a
  later point (e.g. after a related article has been published).
- Requests are mailed to Public Bodies through the platform via a special,
  request-unique email address (using SMTP) and the platform will receive answers on
  that mail address (by accessing an IMAP account).
- Search functionality for Requests and Public Bodies.
- A read/write REST-API
- Redaction of PDFs

Dependencies
------------

A detailed list of Python package dependencies can be found in `requirements.txt`, but here is a general overview:

- Django 1.5 - the Web framework
- Celery 3.X - task queue for background processing
- Haystack 2.X-beta - abstraction layer for search

A development goal is that, even though a task queue (like Celery) and a search server (like Solr) are highly recommended, they are not necessary for either development or production setup and can be replaced with Cronjobs and database queries respectively (results/performance will probably degrade, but it will work nonetheless).

History
-------

Froide was designed to mimic the functionality of `What do they know <http://whatdotheyknow.com>`_ – a Freedom of Information portal in the UK written in Ruby on Rails 2.3. At the time when a German FoI portal was needed, the general FoI solution forked from WDTK called `Alaveteli <http://alaveteli.org>`_ was hard to install and not ready for reuse.
That's why Froide was developed in spring 2011 as a fresh start, fully
internationalized and configurable written in Django 1.3 to power `Frag den Staat <https://fragdenstaat.de>`_ which launched in August 2011.

Name
----

Froide stems from "Freedom of Information de" (de for Germany) and sounds
like the German word "Freude" which means joy.

