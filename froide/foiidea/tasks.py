import sys

from celery.task import task

from django.conf import settings
from django.utils import translation
from django.db import transaction

from foiidea.crawler import crawl_source_by_id


@task
def fetch_articles(source_id):
    translation.activate(settings.LANGUAGE_CODE)

    def run(source_id):
        try:
            crawl_source_by_id(int(source_id))
        except Exception:
            transaction.rollback()
            return sys.exc_info()
        else:
            transaction.commit()
            return None
    run = transaction.commit_manually(run)
    exc_info = run(source_id)
    if exc_info is not None:
        from sentry.client.models import client
        client.create_from_exception(exc_info=exc_info, view="froide.foiidea.tasks.fetch_articles")
