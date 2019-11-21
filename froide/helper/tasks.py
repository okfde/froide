import logging

from django_elasticsearch_dsl.registries import registry
from django.apps import apps

from froide.celery import app as celery_app

logger = logging.getLogger(__name__)


def get_instance(model_name, pk):
    model = apps.get_model(model_name)
    try:
        return model._default_manager.get(pk=pk)
    except model.DoesNotExist:
        return None


@celery_app.task
def search_instance_save(model_name, pk):
    instance = get_instance(model_name, pk)
    if instance is None:
        return
    try:
        registry.update(instance)
        registry.update_related(instance)
    except Exception as e:
        logger.exception(e)


@celery_app.task
def search_instance_pre_delete(model_name, pk):
    instance = get_instance(model_name, pk)
    if instance is None:
        return
    try:
        registry.delete_related(instance)
    except Exception as e:
        logger.exception(e)


@celery_app.task
def search_instance_delete(model_name, pk):
    if pk is None:
        return
    model = apps.get_model(model_name)
    instance = model()
    instance.pk = pk
    instance.id = pk
    registry.delete(instance, raise_on_error=False)
