export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

test:
	flake8 check
	coverage run --branch -m pytest froide/
	coverage report

testui:
	coverage run --branch -m pytest --browser chromium froide/tests/live/

.PHONY: htmlcov
htmlcov:
	coverage html

messagesde:
	django-admin makemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --add-location file

requirements: pyproject.toml
	uv pip compile -o requirements.txt pyproject.toml
	uv pip compile -o requirements-test.txt --extra test pyproject.toml
