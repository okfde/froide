================
Production Setup
================

This is an example of a production setup, your personal flavor may vary.

- Nginx as a frontend server
- Supervisor as process manager and monitor
- Gunicorn as WSGI Server
- RabbitMQ as Background Queue Broker
- Solr as Search Engine


Protect admin site
------------------

Setup your front end server to serve the admin site behind basic authentication.
Here is an example for Nginx::

  location /custom-admin-url {
    auth_basic "Restricted";
    auth_basic_user_file  /var/www/froide/conf/htadminsitepasswd;
    proxy_pass http://127.0.0.1:29000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Protocol https;
  }

Also note that we forward the HTTPS protocol. This sh

- Protect the admin by setting a Basic Authentication via Nginx for the URL
- Make the URL secret via the `SECRET_URLS` setting


Acces to Documents
------------------

Nginx is able to serve your uploads behind authentication/authorization. Activate the following settings::

  # Use nginx to serve uploads authenticated
  USE_X_ACCEL_REDIRECT = True
  X_ACCEL_REDIRECT_PREFIX = '/protected'

Nginx will forward the request to Froide which will in turn check for authentication and authorization. If everything is good Froide replies to Nginx with an internal redirect and Nginx will then serve the file to the user.

A sample configuration looks like this::

  location /protected {
    internal;
    alias /var/www/froide/public;
  }
