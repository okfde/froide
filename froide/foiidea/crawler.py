# -*- coding: utf-8 -*-
import time
from datetime import datetime

import requests

from django.utils import timezone

from .crawlers import rss
from .models import Source, Article

CRAWLER = {
    'rss': rss
}

BOOSTERS = {
    u'dokument': 1,
    u'akte': 1,
    u'informationsfreiheit': 2,
    u'gutachten': 2,
    u'vertrag': 2,
    u'sponsoring': 2,
    u'öpp': 3,
    u'geheim': 3,
    u'vertraulich': 3,
    u'unveröffentlicht': 3
}


def crawl_source_by_id(source_id):
    try:
        source = Source.objects.get(id=source_id)
    except Source.DoesNotExist:
        return None
    return crawl_source(source)


def crawl_source(source):
    public_bodies = None
    response = requests.get(source.url)
    crawler = CRAWLER[source.crawler]
    items = crawler.convert_to_items(response.content)
    article_count = 0
    for item in items:
        count = Article.objects.filter(url=item['url']).count()
        if count:
            continue
        text = item['text']
        lower_text = item['text'].lower()

        # Try to match public bodies
        if public_bodies is None:
            from froide.publicbody.models import PublicBody
            public_bodies = PublicBody.objects.all().values_list('id', 'name', 'other_names')
        pbs = []
        for public_body_id, name, other_names in public_bodies:
            if (name.lower() in lower_text or
                any([x.strip() in text for x in other_names.split(',')
                    if x.strip()])):
                pbs.append(public_body_id)

        if not pbs:
            continue

        # Calculate a score from terms
        item['score'] = min(len(pbs), 3)
        for boost in BOOSTERS:
            if boost in lower_text:
                item['score'] += BOOSTERS[boost] * 10

        if item['date'] is not None:
            item['date'] = datetime.fromtimestamp(time.mktime(item['date']))
            item['date'] = timezone.make_aware(item['date'],
                                               timezone.get_current_timezone())
        else:
            item['date'] = timezone.now()
        item.update({'source': source})

        article = Article(**item)
        article.set_order()
        article.save()
        article.public_bodies.add(*pbs)

        article_count += 1

    source.last_crawled = datetime.utcnow()
    source.save()
    return article_count
