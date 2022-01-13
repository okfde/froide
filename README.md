# Froide

[![Froide CI](https://github.com/okfde/froide/workflows/Froide%20CI/badge.svg)](https://github.com/okfde/froide/actions?query=workflow%3A%22Froide+CI%22) [![Coverage Status](https://coveralls.io/repos/github/okfde/froide/badge.svg?branch=main)](https://coveralls.io/r/okfde/froide?branch=main)


Froide is a Freedom Of Information Portal using Django 3.2 on Python 3.8+.

It is used by the German and the Austrian FOI site, but it is fully
internationalized and written in English.

## Development on Froide

After clone, create a Python 3.8+ virtual environment and install dependencies:

```
python3 -m venv froide-env
source froide-env/bin/activate

# Install dev dependencies
pip install -r requirements-test.txt

# Install git pre-commit hook
pre-commit install
```

### Start services

You can run your own Postgres+PostGIS database and Elasticsearch service or run them with Docker.

You need [docker](https://www.docker.com/community-edition) and [docker-compose](https://docs.docker.com/compose/). Make sure Docker is running and use the following command:

```
docker-compose up
```

This will start Postgres and Elasticsearch and listen on port 5432 and 9200 respectively. You can adjust the port mapping in the `docker-compose.yml`.


### Upgrade dependencies

```
# with pip-tools
pip-compile -U requirements.in
pip-compile -U requirements-test.in
```

### Setup database and search index, start server

If you need to adjust settings, you can copy the `froide/local_settings.py.example` to `froide/local_settings.py` and edit it. More steps:

```
# To initialise the database:
python manage.py migrate --skip-checks
# Create a superuser
python manage.py createsuperuser
# Create and populate search index
python manage.py search_index --create
python manage.py search_index --populate
# Run the Django development server
python manage.py runserver
```

## Run tests

Make sure the services are running.

```
# Run all tests
make test
# Run only unit/integration tests
make testci
# Run only end-to-end tests
make testui
```

## Docs

[Read the documentation](http://froide.readthedocs.org/en/latest/) including a [Getting Started Guide](http://froide.readthedocs.org/en/latest/gettingstarted/).

Froide is supported by the [Open Knowledge Foundation Germany](http://www.okfn.de/) and [Open Knowledge Foundation International](http://okfn.org/).


## License

Froide is licensed under the MIT License.
