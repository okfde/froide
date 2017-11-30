from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, redirect

from froide.helper.utils import render_403

from ..models import FoiProject


def project_shortlink(request, pk):
    foiproject = get_object_or_404(FoiProject, pk=pk)
    if foiproject.is_visible(request.user):
        return redirect(foiproject)
    else:
        return render_403(request)


class ProjectView(DetailView):
    model = FoiProject
    # FIXME
