from django.shortcuts import render

from foiidea.models import Article


def index(request):
    return render(request, 'foiidea/index.html', {
        'object_list': Article.objects.all().select_related('public_bodies', 'foirequests')
    })
