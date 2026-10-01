export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

test:
	ruff check
	pytest --cov froide/

.PHONY: htmlcov
htmlcov:
	coverage html

backend_dependencies:
	uv sync --upgrade-package django-filingcabinet

frontend_dependencies:
	pnpm update @okfde/filingcabinet

dependencies: backend_dependencies frontend_dependencies

PYTHON ?= .venv/bin/python
MAKEMESSAGES_OPTS = --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --add-location file --no-wrap --sort-output --keep-header
MAKEMESSAGES_EXTRA_OPTS =

messagesde:
	$(PYTHON) manage.py extendedmakemessages -l de $(MAKEMESSAGES_OPTS) $(MAKEMESSAGES_EXTRA_OPTS)

checkmessagesde:
	$(MAKE) messagesde MAKEMESSAGES_EXTRA_OPTS="--no-untranslated --no-fuzzy"

openapi:
	python manage.py spectacular --file froide/openapi-schema.yaml --validate
	pnpm run openapi
