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
    yield from dict_to_csv_stream(export_dict_stream(queryset, fields))


def export_dict_stream(queryset, fields):
    for obj in queryset:
        if hasattr(obj, 'get_dict'):
            d = obj.get_dict(fields)
        else:
            d = get_dict(obj, fields)
        yield d


def dict_to_csv_stream(stream):
    writer = None
    fake_file = FakeFile()
    for d in stream:
        if writer is None:
            field_names = list(d.keys())
            writer = csv.DictWriter(fake_file, field_names)
            writer.writeheader()
            yield fake_file._last_string
        writer.writerow(d)
        yield fake_file._last_string


def export_csv_bytes(generator):
    return bytes().join(generator)
