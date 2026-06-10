import csv
import re
from datetime import datetime
from typing import Generator

from django.http import StreamingHttpResponse

FORMULA_START = re.compile(r"^([=\+\-@])")


def export_csv_response(generator, name="export.csv"):
    response = StreamingHttpResponse(generator, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="%s"' % name
    return response


class FakeFile(object):
    string_buffer: list[str]

    def __init__(self, encoding="utf-8"):
        self._encoding = encoding
        self.string_buffer = []

    def write(self, string: str):
        self.string_buffer.append(string)

    def read_bytes(self):
        return_bytes = bytes().join(
            s.encode(self._encoding) for s in self.string_buffer
        )
        self.string_buffer = []
        return return_bytes


def get_dict(obj, fields):
    d = {}

    for field in fields:
        if isinstance(field, tuple):
            field_name = field[0]
        else:
            field_name = field
        if field_name in d:
            continue
        if isinstance(field, tuple):
            value = field[1](obj)
        else:
            value = obj
            for f in field.split("__"):
                value = getattr(value, f, None)
                if value is None:
                    break
        if value is None:
            d[field_name] = ""
        elif isinstance(value, datetime):
            d[field_name] = value.isoformat()
        else:
            d[field_name] = str(value)
    return d


def export_csv(queryset, fields):
    yield from dict_to_csv_stream(export_dict_stream(queryset, fields))


def export_dict_stream(queryset, fields) -> Generator[dict, None, None]:
    for obj in queryset:
        if hasattr(obj, "get_dict"):
            d = obj.get_dict(fields)
        else:
            d = get_dict(obj, fields)
        yield d


def sanitize_row(row):
    for k, v in row.items():
        row[k] = FORMULA_START.sub("'\\1", str(v))
    return row


def dict_to_csv_stream(
    stream, encoding="utf-8", delimiter=","
) -> Generator[bytes, None, None]:
    writer = None
    fake_file = FakeFile(encoding=encoding)
    for d in stream:
        if writer is None:
            field_names = list(d.keys())
            writer = csv.DictWriter(fake_file, field_names, delimiter=delimiter)
            writer.writeheader()
            yield fake_file.read_bytes()
        writer.writerow(sanitize_row(d))
        yield fake_file.read_bytes()


def export_csv_bytes(generator: Generator[bytes, None, None]) -> bytes:
    return bytes().join(generator)
