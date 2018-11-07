from django.db.models import signals
from django.dispatch import receiver

from .models import ProblemReport
from .utils import inform_managers


@receiver(signals.post_save, sender=ProblemReport,
        dispatch_uid="report_problem_to_managers")
def report_problem_to_managers(instance=None, created=False, **kwargs):
    if kwargs.get('raw', False):
        return
    if not created:
        return
    inform_managers(instance)
