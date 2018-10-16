from django_elasticsearch_dsl.registries import registry

from froide.celery import app as celery_app


@celery_app.task
def search_instance_save(instance):
    try:
        registry.update(instance)
        registry.update_related(instance)
    except Exception:
        pass


@celery_app.task
def search_instance_pre_delete(instance):
    try:
        registry.delete_related(instance)
    except Exception:
        pass


@celery_app.task
def search_instance_delete(instance):
    registry.delete(instance, raise_on_error=False)
