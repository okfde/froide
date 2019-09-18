from django.utils.http import urlencode
from django.urls import reverse, NoReverseMatch


def make_filter_url(url_name, data=None, get_active_filters=None):
    if data is None:
        data = {}
    data = dict(data)
    url_kwargs = {}

    if get_active_filters is None:
        active_filters = {}
    else:
        active_filters = get_active_filters(data)

    for key in active_filters:
        url_kwargs[key] = data.pop(key)

    query_string = ''
    data = {k: v for k, v in data.items() if v}
    if data:
        query_string = '?' + urlencode(data)
    try:
        return reverse(url_name, kwargs=url_kwargs) + query_string
    except NoReverseMatch:
        return ''


def get_facet_with_label(info, model=None, attr='name'):
    pks = [item['key'] for item in info['buckets']]
    objs = {
        o.pk: o for o in model.objects.filter(pk__in=pks)
    }
    for item in info['buckets']:
        yield {
            'label': getattr(objs[item['key']], attr),
            'id': item['key'],
            'count': item['doc_count']
        }


def key_getter(item):
    return item['key']


class FakeObject():
    def __getattr__(self, name):
        return ''


def resolve_facet(data, getter=None, label_getter=None,
                query_param=None, model=None, make_url=None):
    if getter is None:
        getter = key_getter

    if label_getter is None:
        label_getter = key_getter

    def resolve(key, info):
        query_key = query_param or key
        if model is not None:
            pks = [item['key'] for item in info['buckets']]
            objs = {
                str(o.pk): o for o in model._default_manager.filter(pk__in=pks)
            }
            for item in info['buckets']:
                if item['key'] in objs:
                    item['object'] = objs[item['key']]
                else:
                    item['object'] = FakeObject()
        for item in info['buckets']:
            item['active'] = getter(item) == data.get(query_key)
            item['label'] = label_getter(item)
            d = data.copy()
            d[query_key] = getter(item)
            item['url'] = make_url(d)
            d.pop(query_key)
            item['clear_url'] = make_url(d)
        return info
    return resolve
