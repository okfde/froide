export DJANGO_SETTINGS_MODULE=froide.test_settings

createenv:
	pip install terrarium boto
	terrarium key requirements-test.txt
	terrarium --target froideenv --remote-key-format "u/stwe/froideenv/%(arch)s-%(python_vmajor)s.%(python_vminor)s-%(digest)s" install requirements-test.txt || (wget "http://resources.opendatalabs.org.s3.amazonaws.com/u/stwe/froideenv/`terrarium key requirements-test.txt`" ; terrarium --target froideenv --storage-dir . install requirements-test.txt)

test:
	pep8 --ignore=E501,E124,E126,E127,E128 --exclude=migrations froide
	coverage run --branch --source=froide `which django-admin.py` test froide.account.tests froide.foirequest.tests froide.foirequestfollower.tests froide.frontpage.tests froide.publicbody.tests
	coverage report --omit="*/migrations/*"

live:
	coverage run --branch --source=froide `which django-admin.py` test froide.tests.live