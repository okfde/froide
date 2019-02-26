class SearchRegistry(object):
    def __init__(self):
        self.searches = []

    def register(self, func):
        self.searches.append(func)

    def get_searches(self, request):
        sections = []
        for callback in self.searches:
            menu_item = callback(request)
            if menu_item is None:
                continue
            sections.append(menu_item)
        sections = sorted(sections, key=lambda x: x['title'])
        return sections


search_registry = SearchRegistry()
