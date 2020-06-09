export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

test:
	flake8 froide
	coverage run --branch manage.py test froide --keepdb
	coverage report

testci:
	coverage run --branch manage.py test froide --exclude-tag ui --keepdb
	coverage report

testui:
	coverage run python manage.py test froide.tests.live --keepdb

.PHONY: htmlcov
htmlcov:
	coverage html
