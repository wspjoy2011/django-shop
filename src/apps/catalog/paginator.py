from typing import Any, Callable, Optional, Sequence, Generic, Iterator

from django.core.paginator import Paginator, Page

from .protocols import SupportsCountSlice, ItemT


class AdaptiveKeysPaginator(Paginator):
    """
    Paginator that can fetch page data via an external strategy using only page number
    and page size, falling back to slicing the original object_list when not provided.
    """

    def __init__(
            self,
            object_list: SupportsCountSlice[ItemT],
            per_page: int,
            orphans: int = 0,
            allow_empty_first_page: bool = True,
            *,
            data_strategy: Optional[Callable[[int, int], Optional[Sequence[ItemT]]]] = None,
    ) -> None:
        """
        Initialize paginator with an optional external data strategy.

        Args:
            object_list: Source sequence to paginate.
            per_page: Items per page.
            orphans: Minimum orphans allowed on the last page.
            allow_empty_first_page: Whether an empty first page is permitted.
            data_strategy: Callback receiving (page_number, page_size) and returning
                a sequence of items for that page or None to fallback.

        Side Effects:
            Stores the provided strategy for later use in page() calls.
        """
        self._data_strategy = data_strategy
        super().__init__(object_list, per_page, orphans, allow_empty_first_page)

    def page(self, number: int) -> Page:
        """
        Return a Page for the given 1-based page number.

        Args:
            number: 1-based page number.

        Returns:
            Page: Page object containing items for the requested number.

        Side Effects:
            If a data_strategy is set, it will be invoked to get page items.
        """
        number = self.validate_number(number)
        if self._data_strategy:
            data = self._data_strategy(number, self.per_page)
            if data is not None:
                return Page(data, number, self)

        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        return Page(self.object_list[bottom:top], number, self)


class QuerySetWithCount(SupportsCountSlice[ItemT], Generic[ItemT]):
    """
    Lightweight wrapper providing a fixed count for an underlying queryset-like
    object to avoid repeated COUNT queries while retaining slicing semantics.
    """

    def __init__(self, queryset: Any, count: int) -> None:
        """
        Wrap a queryset with a cached total count.

        Args:
            queryset: Underlying queryset or sliceable object.
            count: Precomputed total number of items.
        """
        self.queryset = queryset
        self._count = count

    def count(self) -> int:
        """
        Return the cached total count.

        Returns:
            int: Total number of items.
        """
        return self._count

    def __len__(self) -> int:
        """
        Return the cached total count for len().

        Returns:
            int: Total number of items.
        """
        return self._count

    def __getitem__(self, item: Any) -> Any:
        """
        Delegate slicing/indexing to the underlying queryset.

        Args:
            item: Index or slice.

        Returns:
            Any: Indexed item or slice result from the underlying queryset.
        """
        return self.queryset[item]

    def __iter__(self) -> Iterator[ItemT]:
        return iter(self.queryset)
