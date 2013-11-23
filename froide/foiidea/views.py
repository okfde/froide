from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Article


def index(request):
    page = request.GET.get('page')
    paginator = Paginator(Article.objects.get_ordered(), 20)
    try:
        articles = paginator.page(page)
    except PageNotAnInteger:
        articles = paginator.page(1)
    except EmptyPage:
        articles = paginator.page(paginator.num_pages)

    return render(request, 'foiidea/index.html', {
        'object_list': articles
    })


def show(request, article_id):
    return render(request, 'foiidea/show.html', {
        'object': get_object_or_404(Article, id=int(article_id))
    })
