'''
This needs it's own module due to import cycles
as it the class here is referenced in settings.
'''

from rest_framework_csv.renderers import PaginatedCSVRenderer


class CustomPaginatedCSVRenderer(PaginatedCSVRenderer):
    """
    Our pagination has an objects level with additional facets
    This renderer only renders results
    """
    def render(self, data, *args, **kwargs):
        if not isinstance(data, list):
            data = data.get('objects', {}).get('results', [])
        return super(PaginatedCSVRenderer, self).render(data, *args, **kwargs)
