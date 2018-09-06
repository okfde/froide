import csv

from django.http import StreamingHttpResponse


def export_csv_response(generator, name='export.csv'):
    response = StreamingHttpResponse(generator, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' % name
    return response


class FakeFile(object):
    def write(self, string):
        self._last_string = string.encode('utf-8')


def get_dict(obj, fields):
    d = {}

    for field in fields:
        if field in d:
            continue
        if isinstance(field, tuple):
            field_name = field[0]
            value = field[1](obj)
        else:
            value = obj
            field_name = field
            for f in field.split('__'):
                value = getattr(value, f, None)
                if value is None:
                    break
        if value is None:
            d[field_name] = ""
        else:
            d[field_name] = str(value)
    return d


def export_csv(queryset, fields):
    fake_file = FakeFile()
    field_names = [f[0] if isinstance(f, tuple) else f for f in fields]
    writer = csv.DictWriter(fake_file, field_names)
    writer.writeheader()
    yield fake_file._last_string
    for obj in queryset:
        if hasattr(obj, 'get_dict'):
            d = obj.get_dict(fields)
        else:
            d = get_dict(obj, fields)
        writer.writerow(d)
        yield fake_file._last_string


def export_csv_bytes(generator):
    return bytes().join(generator)
