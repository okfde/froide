from django.urls import NoReverseMatch, reverse
from django.utils.http import urlencode


def key_getter(item):
    return item["key"]


class FakeObject:
    def __getattr__(self, name):
        return ""


def get_facet_data(aggregation_item, key):
    if key in aggregation_item:
        # the data could ne nested due to aggs filter
        return aggregation_item[key]
    return aggregation_item


class SearchManager:
    def __init__(
        self,
        facet_config,
        url_kwargs,
        filter_data,
        filter_order=None,
        sub_filters=None,
        search_url_name="",
    ):
        self.facet_config = facet_config

        self.filter_order = filter_order
        self.sub_filters = sub_filters
        self.search_url_name = search_url_name
        self.url_kwargs = url_kwargs

        self.filter_data = self.get_filter_data(url_kwargs, filter_data)

    def get_filter_data(self, filter_kwargs, data):
        query = {}
        for key in self.get_active_filters(filter_kwargs):
            query[key] = filter_kwargs[key]
        data.update(query)
        return data

    def get_active_filters(self, data):
        return list(
            get_active_filters(data, self.filter_order, sub_filters=self.sub_filters)
        )

    def make_filter_url(self, data=None):
        if data is None:
            data = self.filter_data
        active_filters = self.get_active_filters(data)
        return make_filter_url(
            self.search_url_name, data=data, active_filters=active_filters
        )

    def get_pagination_vars(self):
        """
        Returns the query parameters the should be kept when pagination (i.e. filters etc that
        should be kept on the next pages)

        This is used to remove filters in the path (i.e. /requests/<jurisdiction>/) from filters
        in the query parameters, so we don't generate a url like
        /requests/example-jurisdiction/?jurisdiction=example-jurisdiction
        """
        data = self.filter_data.copy()
        data = {k: v for k, v in data.items() if v and k not in self.url_kwargs}
        if data:
            return "&" + urlencode(data)
        return ""

    def get_facets(self, aggregation_data):
        return {
            key: self.resolve_facet(
                key,
                get_facet_data(aggregation_data[key], key),
                getter=config.get("getter"),
                model=config.get("model"),
                queryset=config.get("queryset"),
                query_param=config.get("query_param", key),
                label_getter=config.get("label_getter"),
            )
            for key, config in self.facet_config.items()
            if key in aggregation_data
        }

    def resolve_facet(
        self,
        key,
        info,
        getter=None,
        label_getter=None,
        query_param=None,
        model=None,
        queryset=None,
    ):
        if getter is None:
            getter = key_getter

        if label_getter is None:
            label_getter = key_getter

        query_key = query_param or key
        objs = None
        pks = [item["key"] for item in info["buckets"]]
        if queryset is not None:
            objs = {str(o.pk): o for o in queryset.filter(pk__in=pks)}
        elif model is not None:
            objs = {str(o.pk): o for o in model._default_manager.filter(pk__in=pks)}

        if objs is not None:
            for item in info["buckets"]:
                item_key = str(item["key"])
                if item_key in objs:
                    item["object"] = objs[item_key]
                else:
                    item["object"] = FakeObject()
        for item in info["buckets"]:
            item["active"] = getter(item) == self.filter_data.get(query_key)
            item["label"] = label_getter(item)
            d = self.filter_data.copy()
            d[query_key] = getter(item)
            item["url"] = self.make_filter_url(d)
            d.pop(query_key)
            item["clear_url"] = self.make_filter_url(d)
        return info


def get_active_filters(data, filter_order, sub_filters=None):
    if not filter_order:
        return
    for key in filter_order:
        if not data.get(key):
            continue
        yield key
        if sub_filters:
            sub_filters = sub_filters.get(key, ())
            for sub_key in sub_filters:
                if data.get(sub_key):
                    yield sub_key
                    break
        break


def make_filter_url(url_name, data=None, active_filters=None):
    if data is None:
        data = {}
    data = dict(data)
    url_kwargs = {}

    if active_filters is None:
        active_filters = {}

    for key in active_filters:
        url_kwargs[key] = data.pop(key)

    query_string = ""
    data = {k: v for k, v in data.items() if v}
    if data:
        query_string = "?" + urlencode(data)
    try:
        return reverse(url_name, kwargs=url_kwargs) + query_string
    except NoReverseMatch:
        return ""
