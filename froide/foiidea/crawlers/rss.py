from StringIO import StringIO

from lxml import etree
import feedparser


def convert_to_items(data):
    html_parser = etree.HTMLParser()
    feed = feedparser.parse(data)
    for item in feed.entries:
        text = etree.parse(StringIO(item.description), html_parser)
        text = ''.join(text.getroot().itertext()).strip()
        try:
            date = item.published_parsed
        except AttributeError:
            date = None
        link = item.link.split('#')[0]
        yield dict(title=item.title, text=text, url=link, date=date)

if __name__ == '__main__':
    import sys
    print list(convert_to_items(file(sys.argv[1]).read()))
