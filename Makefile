export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

RUN = uv run --no-sync

test:
	$(RUN) ruff check
	$(RUN) pytest --cov froide/

.PHONY: htmlcov
htmlcov:
	$(RUN) coverage html

backend_dependencies:
	# Upgrade django-filingcabinet in uv.lock, but keep its editable install in the venv
	uv sync --all-extras --inexact --no-install-package django-filingcabinet --upgrade-package django-filingcabinet

frontend_dependencies:
	pnpm update @okfde/filingcabinet

dependencies: backend_dependencies frontend_dependencies

MAKEMESSAGES_OPTS = --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --add-location file --no-wrap --sort-output --keep-header
MAKEMESSAGES_EXTRA_OPTS =

messagesde:
	$(RUN) python manage.py extendedmakemessages -l de $(MAKEMESSAGES_OPTS) $(MAKEMESSAGES_EXTRA_OPTS)

checkmessagesde:
	$(MAKE) messagesde MAKEMESSAGES_EXTRA_OPTS="--no-untranslated --no-fuzzy"

openapi:
	$(RUN) python manage.py spectacular --file froide/openapi-schema.yaml --validate
	pnpm run openapi
