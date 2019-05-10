export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

test:
	flake8 --ignore=E501,E123,E124,E126,E127,E128,E402,E731,C901,W504 froide
	coverage run --branch manage.py test froide --keepdb --parallel
	coverage report

.PHONY: htmlcov
htmlcov:
	coverage html
