export DJANGO_SETTINGS_MODULE=froide.settings
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

lint:
	pre-commit run --all

test:
	pytest --cov froide -n auto -m "not elasticsearch"
	pytest --cov froide --cov-append -m "elasticsearch"

testui:
	coverage run --branch -m pytest --browser chromium froide/tests/live/

.PHONY: htmlcov
htmlcov:
	coverage html

messagesde:
	python manage.py makemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --add-location file

requirements: pyproject.toml
	uv pip compile -p 3.10 -o requirements.txt pyproject.toml
	uv pip compile -p 3.10 -o requirements-test.txt --extra test pyproject.toml
