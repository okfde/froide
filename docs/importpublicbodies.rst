=======================
Importing Public Bodies
=======================

While it is possible to create public bodies individually through the admin
interface, it might be more advisable to scrape a list from a website or
crowdsource them with other people in a Google doc. You can then import these
public bodies as a CSV file into Froide.

The format of the CSV file should be like `in this Google Docs Spreadsheet <https://docs.google.com/spreadsheet/ccc?key=0AhDkodM9ozpddGNTaGJoa203aEJaRXVfM0Q0d1RjNUE#gid=0>`_. You could for example copy it and either fill in public bodies collaboratively or programmatically.


Prerequisites
-------------

You need at least one User and one `Jurisdiction` present in the database. The jurisdiction's slug must be explictly referenced in the CSV.


Format
------

The format is quite simple.

name
  (required) The name of the public body.
email
  (optional) If you give no email, users will not be able to make requests to this public body. You can fill in email addresses later through the admin.
jurisdiction__slug
  (required) Give the slug of the jurisdiction this public body belongs to.
other_names
  (optional) Possible other, alternative names for the public body separated by commas.
description
  (optional) A text description of the public body.
tags
  (optional) A comma-separated (possibly quoted) list of tags for this public body.
  Tags may already exist or not.
url
  (optional) Website for this public body.
parent__name
  (optional) if this public body has a parent, give it's name here. The parent must be specified before in the CSV file.
classification
  (optional) Give a classification (e.g. "ministry").
contact
  (optional) Contact information apart from post address and email. E.g. phone or fax number. May contain line breaks.
address
  (optional) Postal address of this public body.
website_dump
  (optional) Any further text that can be used to described this public body. This is used for search indexing and will not be displayed publicly.
request_note
  (optional) Display this text for this public body when making a request to it.

If during import a public body with the same slug is found, it is skipped and not overwritten.

Importing through Admin
-----------------------

The admin interface that lists public bodies has an import form at the very bottom of the page. Give a HTTP or HTTPS url of your CSV file and press the import button. The file will be downloaded and imported. Any errors will be shown to you.


Importing via command line
--------------------------

The management command `import_csv` takes a URL or a path to a CSV file::

    python manage.py import_csv public_bodies.csv
