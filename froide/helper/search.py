from haystack.fields import NgramField


try:
    from .elasticsearch import SuggestField
except ImportError:
    class SuggestField(NgramField):
        pass


class SearchQuerySetWrapper(object):
    """
    Decorates a SearchQuerySet object using a generator for efficient iteration
    """
    def __init__(self, sqs, model):
        self.sqs = sqs
        self.model = model

    def count(self):
        return self.sqs.count()

    def __iter__(self):
        for result in self.sqs:
            yield result.object

    def __getitem__(self, key):
        if isinstance(key, int) and (key >= 0 or key < self.count()):
            # return the object at the specified position
            return self.sqs[key].object
        # Pass the slice/range on to the delegate
        return SearchQuerySetWrapper(self.sqs[key], self.model)
