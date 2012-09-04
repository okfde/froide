from celery.task import task

from django.conf import settings
from django.utils import translation

from .crawler import crawl_source_by_id
from .models import Article


@task
def fetch_articles(source_id):
    translation.activate(settings.LANGUAGE_CODE)
    crawl_source_by_id(int(source_id))


@task
def recalculate_order():
    Article.objects.recalculate_order()
