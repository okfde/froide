from django.core.paginator import Paginator


class ElasticsearchPaginator(Paginator):
    """
    Paginator that prevents two queries to ES (for count and objects)
    as ES gives count with objects
    """
    MAX_ES_OFFSET = 10000

    def page(self, number):
        """
        Returns a Page object for the given 1-based page number.
        """
        bottom = (number - 1) * self.per_page
        if bottom >= self.MAX_ES_OFFSET:
            # Only validate if bigger than offset
            number = self.validate_number(number)
            bottom = (number - 1) * self.per_page

        top = bottom + self.per_page
        self.object_list = self.object_list[bottom:top]

        # ignore top boundary
        # if top + self.orphans >= self.count:
        #     top = self.count

        # Validate number after limit/offset has been set
        number = self.validate_number(number)
        return self._get_page(self.object_list, number, self)
