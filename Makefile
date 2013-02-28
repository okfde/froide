export DJANGO_SETTINGS_MODULE=froide.settings_test

test:
	pep8 --ignore=E501,E124,E126,E127,E128 --exclude=migrations froide
	coverage run --branch --source=froide `which django-admin.py` test froide
	coverage report --omit="*/migrations/*"
