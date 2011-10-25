time coverage run --source=. manage.py test --settings=test_settings $* && coverage html --omit="*/migrations/*"
