from __future__ import unicode_literals

import datetime
import json

from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.sitemaps import Sitemap

from froide.publicbody.models import PublicBody
from froide.frontpage.models import FeaturedRequest
from froide.helper.utils import render_403
from froide.helper.cache import cache_anonymous_page

from ..models import FoiRequest
from ..tasks import process_mail
from ..foi_mail import package_foirequest


X_ACCEL_REDIRECT_PREFIX = getattr(settings, 'X_ACCEL_REDIRECT_PREFIX', '')
User = get_user_model()


@cache_anonymous_page(15 * 60)
def index(request):
    successful_foi_requests = FoiRequest.published.successful()[:8]
    unsuccessful_foi_requests = FoiRequest.published.unsuccessful()[:8]
    featured = FeaturedRequest.objects.getFeatured()
    return render(request, 'index.html',
            {'featured': featured,
            'successful_foi_requests': successful_foi_requests,
            'unsuccessful_foi_requests': unsuccessful_foi_requests,
            'foicount': FoiRequest.published.for_list_view().count(),
            'pbcount': PublicBody.objects.get_list().count()
        })


def dashboard(request):
    if not request.user.is_staff:
        return render_403(request)
    context = {}
    user = {}
    start_date = timezone.utc.localize(datetime.datetime(2011, 7, 30))
    for u in User.objects.filter(
            is_active=True,
            date_joined__gte=start_date):
        d = u.date_joined.date().isoformat()
        user.setdefault(d, 0)
        user[d] += 1
    context['user'] = sorted([{'date': k, 'num': v, 'symbol': 'user'} for k, v in user.items()], key=lambda x: x['date'])
    total = 0
    for user in context['user']:
        total += user['num']
        user['total'] = total
    foirequest = {}
    foi_query = FoiRequest.objects.filter(
            is_foi=True,
            public_body__isnull=False,
            first_message__gte=start_date
    )
    if request.GET.get('notsameas'):
        foi_query = foi_query.filter(same_as__isnull=True)
    if request.GET.get('public'):
        foi_query = foi_query.filter(visibility=FoiRequest.VISIBLE_TO_PUBLIC)
    for u in foi_query:
        d = u.first_message.date().isoformat()
        foirequest.setdefault(d, 0)
        foirequest[d] += 1
    context['foirequest'] = sorted([{'date': k, 'num': v, 'symbol': 'user'} for k, v in foirequest.items()], key=lambda x: x['date'])
    total = 0
    for req in context['foirequest']:
        total += req['num']
        req['total'] = total
    return render(request, 'foirequest/dashboard.html', {'data': json.dumps(context)})


@require_POST
@csrf_exempt
def postmark_inbound(request, bounce=False):
    process_mail.delay(request.body, mail_type='postmark')
    return HttpResponse()


@require_POST
@csrf_exempt
def postmark_bounce(request):
    return postmark_inbound(request, bounce=True)


def download_foirequest(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_staff and not request.user == foirequest.user:
        return render_403(request)
    response = HttpResponse(package_foirequest(foirequest), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s.zip"' % foirequest.pk
    return response


SITEMAP_PROTOCOL = 'https' if settings.SITE_URL.startswith('https') else 'http'


class FoiRequestSitemap(Sitemap):
    protocol = SITEMAP_PROTOCOL
    changefreq = "hourly"
    priority = 0.5

    def items(self):
        return FoiRequest.published.all()

    def lastmod(self, obj):
        return obj.last_message
