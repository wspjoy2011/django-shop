from typing import Callable, Optional, Sequence

from django.core.paginator import Paginator, Page


class AdaptiveKeysPaginator(Paginator):

    def __init__(
            self,
            object_list,
            per_page,
            orphans=0,
            allow_empty_first_page=True,
            *,
            data_strategy: Optional[Callable[[int, int], Optional[Sequence]]] = None,
    ):
        self._data_strategy = data_strategy
        super().__init__(object_list, per_page, orphans, allow_empty_first_page)

    def page(self, number):
        number = self.validate_number(number)
        if self._data_strategy:
            data = self._data_strategy(number, self.per_page)
            if data is not None:
                return Page(data, number, self)

        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        return Page(self.object_list[bottom:top], number, self)


class QuerySetWithCount:
    def __init__(self, queryset, count):
        self.queryset = queryset
        self._count = count

    def count(self):
        return self._count

    def __len__(self):
        return self._count

    def __getitem__(self, item):
        return self.queryset[item]
