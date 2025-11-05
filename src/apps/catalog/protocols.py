from typing import overload, TypeVar, Protocol, Sequence, Any, Iterator

from django.db.models import Manager, Model
from django.db.models.options import Options

ItemT = TypeVar("ItemT")
ModelT = TypeVar("ModelT", bound=Model)


class ModelClassWithManager(Protocol[ModelT]):
    objects: Manager[ModelT]
    _meta: Options


class SupportsUserAuth(Protocol):
    @property
    def is_authenticated(self) -> bool: ...

    id: int


class MaterializedViewModel(Protocol):
    """Protocol for materialized view models with class-level refresh API."""
    _meta: Any

    @classmethod
    def refresh(cls, concurrently: bool = ...) -> None: ...


class SupportsCountSlice(Protocol[ItemT]):
    """
    Object that supports Django pagination patterns:
    - __len__ for total size
    - count() -> int for total size (Django prefers this)
    - slicing via __getitem__
    - iteration
    """

    def __len__(self) -> int: ...

    def count(self) -> int: ...

    @overload
    def __getitem__(self, item: int) -> ItemT: ...

    @overload
    def __getitem__(self, item: slice) -> Sequence[ItemT]: ...

    def __getitem__(self, item: int | slice) -> Any: ...

    def __iter__(self) -> Iterator[ItemT]: ...
