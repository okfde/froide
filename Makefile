export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

test:
	flake8 froide
	coverage run --branch -m pytest froide/
	coverage report

testci:
	coverage run --branch -m pytest froide/ --ignore=froide/tests/live/
	coverage report

testui:
	coverage run --branch -m pytest --browser chromium froide/tests/live/

.PHONY: htmlcov
htmlcov:
	coverage html

messagesde:
	django-admin makemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --add-location file

requirements: requirements.in requirements-test.in
	pip-compile requirements.in
	pip-compile requirements-test.in
