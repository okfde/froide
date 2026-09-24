export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

-include Makefile.local

test:
	ruff check
	pytest --cov froide/

.PHONY: htmlcov
htmlcov:
	coverage html

backend_dependencies:
	uv sync --upgrade-package django-filingcabinet $(UV_SYNC_ARGS)

frontend_dependencies:
	pnpm update @okfde/filingcabinet

dependencies: backend_dependencies frontend_dependencies

messagesde:
	python manage.py extendedmakemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --add-location file --no-wrap --sort-output --keep-header

openapi:
	python manage.py spectacular --file froide/openapi-schema.yaml --validate
	pnpm run openapi
