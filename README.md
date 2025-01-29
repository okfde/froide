# Froide

[![Froide CI](https://github.com/okfde/froide/workflows/Froide%20CI/badge.svg)](https://github.com/okfde/froide/actions?query=workflow%3A%22Froide+CI%22)

Froide is a Freedom Of Information Portal using Django 4.2+ on Python 3.10+.

It is used by the German and the Austrian FOI site, but it is fully
internationalized and written in English.

## Development on Froide

Required system tools:
- [make](https://www.gnu.org/software/make/)
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com/) or compatible containerisation tool
- [pnpm](https://pnpm.io/)

Required system libs:
- libpoppler-cpp-dev

After clone, create a Python 3.10+ virtual environment and install dependencies:

```
# create and activate virtual envornment
uv venv
source .venv/bin/activate

# install dependencies
uv pip sync requirements-test.txt

# build froide backend
uv pip install -e . --no-deps

# install UI test browser
playwright install --with-deps chromium

# install node 20
pnpm env use --global 20

#install frontend dependencies
pnpm install

# build froide frontend
pnpm run build

# Install git pre-commit hook
pre-commit install
```

### Start services

You can run your own Postgres+PostGIS database and Elasticsearch service or run them with [Docker](https://docker.com):

```
docker compose -f compose-dev.yaml up
```

This will start Postgres and Elasticsearch and listen on port 5432 and 9200 respectively. You can adjust the port mapping in the `compose-dev.yaml`.

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

### Run tests

Make sure the services are running.

```
# Run all tests
make test
# Run only unit/integration tests
make testci
# Run only end-to-end tests
make testui
```

### Development tooling

For Python code, we use ruff for linting and formatting. JavaScript, Vue and SCSS files are formatted and linted with ESLint and Prettier.

Make sure to have pre-commit hooks registered (`pre-commit install`). For VSCode, [we recommend some extensions](./.vscode/extensions.json)

```json
{
  "eslint.format.enable": true,
  "eslint.packageManager": "pnpm",
  "vetur.format.defaultFormatter.css": "prettier",
  "vetur.format.defaultFormatter.html": "prettier",
  "vetur.format.defaultFormatter.js": "prettier-eslint"
}
```

### Upgrade dependencies

```
make requirements
```

## Docs

[Read the documentation](http://froide.readthedocs.org/en/latest/) including a [Getting Started Guide](http://froide.readthedocs.org/en/latest/gettingstarted/).

Froide is supported by the [Open Knowledge Foundation Germany](http://www.okfn.de/) and [Open Knowledge Foundation International](http://okfn.org/).

## License

Froide is licensed under the MIT License.
