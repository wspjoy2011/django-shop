from typing import List, Tuple

from django.db import transaction
from tqdm import tqdm

from apps.catalog.models import (
    Product,
    ArticleType,
    SubCategory,
    MasterCategory,
    BaseColour,
    Season,
    UsageType,
)


class DjangoCatalogCleaner:
    """
    Clean catalog tables in the correct FK order.
    FK graph:
      Product -> ArticleType -> SubCategory -> MasterCategory
      Product -> BaseColour
      Product -> Season
      Product -> UsageType
    So we delete: Product first, then ArticleType, SubCategory, MasterCategory,
    and independent dimensions: BaseColour, Season, UsageType.
    """

    def __init__(self) -> None:
        self._deletion_plan: List[Tuple[str, object]] = [
            ("Products", Product.objects.all()),
            ("Article types", ArticleType.objects.all()),
            ("Sub-categories", SubCategory.objects.all()),
            ("Master categories", MasterCategory.objects.all()),
            ("Base colours", BaseColour.objects.all()),
            ("Seasons", Season.objects.all()),
            ("Usage types", UsageType.objects.all()),
        ]

    def clean(self) -> None:
        with transaction.atomic():
            for label, qs in tqdm(self._deletion_plan, desc="Cleaning catalog"):
                deleted_count, _ = qs.delete()
                tqdm.write(f"Deleted {deleted_count} rows from {label}")
