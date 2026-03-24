export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

test:
	ruff check
	coverage run --branch -m pytest froide/
	coverage report

testui:
	coverage run --branch -m pytest --browser chromium froide/tests/live/

.PHONY: htmlcov
htmlcov:
	coverage html

messagesde:
	python manage.py extendedmakemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --add-location file --no-wrap --sort-output

openapi:
	python manage.py spectacular --file froide/openapi-schema.yaml --validate
	pnpm run openapi
