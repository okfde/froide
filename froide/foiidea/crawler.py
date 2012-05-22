# -*- coding: utf-8 -*-
import time
import math
from datetime import datetime

import requests

from foiidea.crawlers import rss
from foiidea.models import Source, Article

CRAWLER = {
    'rss': rss
}

# German keywords for now
KEYWORDS = [u'minister', u'amt']

BOOSTERS = {
    u'gutachten': 1,
    u'dokument': 1,
    u'akte': 1,
    u'geheim': 3,
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
        text = item['text'].lower()

        # Test for interestingness
        found = False
        for keyword in KEYWORDS:
            if keyword in text:
                found = True
                break
        if not found:
            continue

        # Calculate a score from terms
        score = 1
        for boost in BOOSTERS:
            if boost in text:
                score += BOOSTERS[boost]
        item['score'] = score

        # Try to match public bodies
        if public_bodies is None:
            from publicbody.models import PublicBody
            public_bodies = PublicBody.objects.all().values_list('id', 'name', 'other_names')
        pbs = []
        for public_body_id, name, other_names in public_bodies:
            if (name.lower() in text or
                any([x.strip().lower() in text for x in other_names.split(',')
                    if x.strip()])):
                pbs.append(public_body_id)
        item['score'] += len(pbs)
        if item['date'] is not None:
            item['date'] = datetime.fromtimestamp(time.mktime(item['date']))
        else:
            item['date'] = datetime.utcnow()
        item.update({'source': source})

        article = Article(**item)
        article.set_order()
        article.save()
        article.public_bodies.add(*pbs)

        article_count += 1

    source.last_crawled = datetime.utcnow()
    source.save()
    return article_count
