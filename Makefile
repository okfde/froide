export DJANGO_SETTINGS_MODULE=froide.test_settings

test:
	pep8 --ignore=E501,E124,E126,E127,E128 --exclude=migrations froide
	coverage run --branch --source=froide `which django-admin.py` test account foirequest publicbody foirequestfollower frontpage
	coverage report --omit="*/migrations/*"
