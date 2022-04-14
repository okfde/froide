import logging
from typing import Optional

from django.apps import apps

from django_elasticsearch_dsl.registries import registry
from elasticsearch.exceptions import ConnectionTimeout

from froide.celery import app as celery_app
from froide.foirequest.models.request import FoiRequest
from froide.helper.email_log_parsing import check_delivery_from_log

logger = logging.getLogger(__name__)


def get_instance(model_name: str, pk: int) -> Optional[FoiRequest]:
    model = apps.get_model(model_name)
    try:
        return model._default_manager.get(pk=pk)
    except model.DoesNotExist:
        return None


@celery_app.task(autoretry_for=(ConnectionTimeout,), retry_backoff=True)
def search_instance_save(model_name: str, pk: int) -> None:
    instance = get_instance(model_name, pk)
    if instance is None:
        return
    try:
        registry.update(instance)
        registry.update_related(instance)
    except Exception as e:
        logger.exception(e)


@celery_app.task
def search_instance_pre_delete(model_name: str, pk: int) -> None:
    instance = get_instance(model_name, pk)
    if instance is None:
        return
    try:
        registry.delete_related(instance)
    except Exception as e:
        logger.exception(e)


@celery_app.task(autoretry_for=(ConnectionTimeout,), retry_backoff=True)
def search_instance_delete(model_name: str, pk: Optional[int]) -> None:
    if pk is None:
        return
    model = apps.get_model(model_name)
    instance = model()
    instance.pk = pk
    instance.id = pk
    registry.delete(instance, raise_on_error=False)


@celery_app.task(expires=60 * 60)
def check_mail_log():
    check_delivery_from_log()
