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
	python manage.py makemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --add-location file

requirements: pyproject.toml
	uv pip compile -o requirements.txt pyproject.toml -p 3.10
	uv pip compile -o requirements-test.txt --extra test pyproject.toml -p 3.10

openapi:
	python manage.py generateschema --file froide/openapi-schema.yaml
	pnpm run openapi
