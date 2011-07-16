from celery.task import task
from haystack import site

@task
def delayed_update(instance_pk, model):
    """ Only index stuff that is known to be public """
    try:
        instance = model.published.get(pk=instance_pk)
    except (model.DoesNotExist, AttributeError):
        return
    site.update_object(instance)

@task
def delayed_remove(instance_pk, model):
    try:
        instance = model.published.get(pk=instance_pk)
    except (model.DoesNotExist, AttributeError):
        return
    site.remove_object(instance)
