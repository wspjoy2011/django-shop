from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest

from .models import MasterCategory, SubCategory, ArticleType


def categories(request: HttpRequest) -> dict[str, QuerySet[MasterCategory]]:
    """
    Context processor that provides a hierarchical structure of catalog categories
    for navigation menus.

    The structure includes master categories with their related subcategories
    and article types, all ordered alphabetically by name.

    Args:
        request (HttpRequest): The incoming HTTP request object.

    Returns:
        dict[str, QuerySet[MasterCategory]]: A context dictionary containing
        the key "nav_categories" with a queryset of master categories,
        each prefetching its subcategories and article types.
    """
    sub_queryset = SubCategory.objects.order_by("name").prefetch_related(
        Prefetch(
            "article_types",
            queryset=ArticleType.objects.order_by("name"),
        )
    )

    master_queryset = (
        MasterCategory.objects
        .order_by("name")
        .prefetch_related(Prefetch("sub_categories", queryset=sub_queryset))
    )

    return {
        "nav_categories": master_queryset
    }
