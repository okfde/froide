# Froide

[![Froide CI](https://github.com/okfde/froide/workflows/Froide%20CI/badge.svg)](https://github.com/okfde/froide/actions?query=workflow%3A%22Froide+CI%22) [![Coverage Status](https://coveralls.io/repos/github/okfde/froide/badge.svg?branch=main)](https://coveralls.io/r/okfde/froide?branch=main)


Froide is a Freedom Of Information Portal using Django 3.1 on Python 3.8+.

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

### Upgrade dependencies

```
# with pip-tools
pip-compile -U requirements.in
pip-compile -U requirements-test.in
```


## Docs

[Read the documentation](http://froide.readthedocs.org/en/latest/) including a [Getting Started Guide](http://froide.readthedocs.org/en/latest/gettingstarted/) and [a Heroku deployment guide](http://froide.readthedocs.org/en/latest/herokudeployment/).

Froide is supported by the [Open Knowledge Foundation Germany](http://www.okfn.de/) and [Open Knowledge Foundation International](http://okfn.org/).


## License

Froide is licensed under the MIT License.
