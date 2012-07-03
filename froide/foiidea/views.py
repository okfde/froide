from django.shortcuts import render, get_object_or_404

from .models import Article


def index(request):
    return render(request, 'foiidea/index.html', {
        'object_list': Article.objects.get_ordered()
    })


def show(request, article_id):
    return render(request, 'foiidea/show.html', {
        'object': get_object_or_404(Article, id=int(article_id))
    })
