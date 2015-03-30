export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test

test:
	flake8 --ignore=E501,E123,E124,E126,E127,E128,E402,E731 --exclude=migrations froide
	coverage run --branch --source=froide manage.py test froide
	coverage report --omit="*/migrations/*"
