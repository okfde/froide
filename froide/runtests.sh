time coverage run --source=. manage.py test --failfast --settings=test_settings && coverage html --omit="*/migrations/*"
