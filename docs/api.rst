==========
Froide API
==========

Froide has a RESTful API that allows structured access to the content
inside your Froide instance.

The Froide API is available at `/api/v1/` and the interactive Froide API documentation is available at `/api/v1/docs/`.

There are additional search endpoints for Public Bodies and FOI Requests at `/api/v1/publicbody/search/` and `/api/v1/request/search/` respectively. Use `q` as the query parameter in a GET request.

GET requests do not need to be authenticated. POST, PUT and DELETE requests have to either carry a valid session cookie and a CSRF token or provide username (you find your username on your profile) and password via Basic Authentication.
