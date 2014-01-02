from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.core import urlresolvers
from django.utils.translation import ugettext_lazy as _, ungettext
from django.contrib import messages
from django.template import TemplateDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from froide.foirequest.models import FoiRequest
from froide.helper.utils import render_400, render_403
from froide.helper.cache import cache_anonymous_page

from .models import (PublicBody,
    PublicBodyTag, FoiLaw, Jurisdiction)
from .csv_import import CSVImporter


def index(request, jurisdiction=None, topic=None):
    publicbodies = PublicBody.objects.get_list()

    if jurisdiction is not None:
        jurisdiction = get_object_or_404(Jurisdiction, slug=jurisdiction)
        publicbodies = publicbodies.filter(jurisdiction=jurisdiction)

    if topic is not None:
        topic = get_object_or_404(PublicBodyTag, slug=topic)
        publicbodies = publicbodies.filter(tags=topic)

    page = request.GET.get('page')
    paginator = Paginator(publicbodies, 50)
    try:
        publicbodies = paginator.page(page)
    except PageNotAnInteger:
        publicbodies = paginator.page(1)
    except EmptyPage:
        publicbodies = paginator.page(paginator.num_pages)

    return render(request, 'publicbody/list.html', {
        'object_list': publicbodies,
        'jurisdictions': Jurisdiction.objects.get_visible(),
        'jurisdiction': jurisdiction,
        'topic': topic,
        'topics': PublicBodyTag.objects.filter(is_topic=True)
    })


@cache_anonymous_page(15 * 60)
def show_jurisdiction(request, slug):
    jurisdiction = get_object_or_404(Jurisdiction, slug=slug)
    context = {
        "object": jurisdiction,
        "pb_count": PublicBody.objects.filter(jurisdiction=jurisdiction).count(),
        "laws": FoiLaw.objects.filter(meta=False,
            jurisdiction=jurisdiction).order_by('priority'),
        "foirequests": FoiRequest.published.filter(jurisdiction=jurisdiction)[:5]
    }
    try:
        return render(request,
            'publicbody/jurisdiction/%s.html' % jurisdiction.slug, context)
    except TemplateDoesNotExist:
        return render(request,
            'publicbody/jurisdiction.html', context)


def show_foilaw(request, slug):
    law = get_object_or_404(FoiLaw, slug=slug)
    context = {"object": law}
    return render(request, 'publicbody/show_foilaw.html', context)


def show_publicbody(request, slug):
    obj = get_object_or_404(PublicBody, slug=slug)
    context = {
        'object': obj,
        'foi_requests': FoiRequest.published.filter(public_body=obj)[:10]
    }
    return render(request, 'publicbody/show.html', context)


@require_POST
def confirm(request):
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff and not request.user.is_superuser:
        return render_403(request)
    try:
        pb = get_object_or_404(PublicBody, pk=int(request.POST.get('public_body', '')))
    except ValueError:
        return render_400(request)
    result = pb.confirm()
    if result is None:
        messages.add_message(request, messages.ERROR,
            _('This request was already confirmed.'))
    else:
        messages.add_message(request, messages.ERROR,
                ungettext('%(count)d message was sent.',
                    '%(count)d messages were sent', result
                    ) % {"count": result})
    return HttpResponseRedirect(
        urlresolvers.reverse('admin:publicbody_publicbody_change',
            args=(pb.id,)))


@require_POST
def import_csv(request):
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff and not request.user.is_superuser:
        return render_403(request)
    if not request.method == 'POST':
        return render_403(request)
    importer = CSVImporter()
    url = request.POST.get('url')
    try:
        if not url:
            raise ValueError(_('You need to provide a url.'))
        importer.import_from_url(url)
    except Exception as e:
        messages.add_message(request, messages.ERROR, str(e))
    else:
        messages.add_message(request, messages.SUCCESS,
            _('Public Bodies were imported.'))
    return HttpResponseRedirect(
        urlresolvers.reverse('admin:publicbody_publicbody_changelist'))
