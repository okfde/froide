from django.conf import settings
from django.utils import translation

from celery.task import task
from haystack import site

@task
def delayed_update(instance_pk, model):
    """ Only index stuff that is known to be public """
    translation.activate(settings.LANGUAGE_CODE)
    try:
        instance = model.published.get(pk=instance_pk)
    except (model.DoesNotExist, AttributeError):
        return
    site.update_object(instance)

@task
def delayed_remove(instance_pk, model):
    translation.activate(settings.LANGUAGE_CODE)
    # Fake an instance (real one is already gone from the DB)
    fake_instance = model()
    fake_instance.pk = instance_pk
    site.remove_object(fake_instance)
