import csv

try:
    import unicodecsv
    has_unicodecsv = True
except ImportError:
    has_unicodecsv = False


def get_csv_dictreader(csvfile, encoding='utf-8'):
    if has_unicodecsv:
        return unicodecsv.DictReader(csvfile, encoding=encoding)
    return csv.DictReader(open(csvfile, newline='', encoding=encoding))


def get_csv_dictwriter(csvfile, fieldnames, encoding='utf-8'):
    if has_unicodecsv:
        return unicodecsv.DictWriter(csvfile, fieldnames, encoding=encoding)
    return csv.DictWriter(open(csvfile, 'w', newline='', encoding=encoding))
