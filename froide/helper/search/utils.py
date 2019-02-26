from django.utils.http import urlencode


def get_pagination_vars(data):
    d = data.copy()
    d.pop('page', None)
    return '&' + urlencode(d)
