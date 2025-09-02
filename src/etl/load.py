from typing import Dict, Iterable, List

from django.db import transaction
from django.utils.text import slugify
from tqdm import tqdm

from apps.catalog.models import (
    MasterCategory,
    SubCategory,
    ArticleType,
    BaseColour,
    Season,
    UsageType,
    Product,
)
from etl.dto import (
    MasterCategoryDTO,
    SubCategoryDTO,
    ArticleTypeDTO,
    BaseColourDTO,
    SeasonDTO,
    UsageTypeDTO,
    ProductDTO,
    ImageDTO,
    CatalogResultDTO,
)


class DjangoCatalogSeeder:
    """
    Seed Django models from CatalogResultDTO (output of your ETL extractor/transformer).
    Uses bulk_create with ignore_conflicts=True where applicable and tqdm for progress.
    """

    def __init__(self, batch_size: int = 5000) -> None:
        self._batch_size = batch_size

    def seed(self, dto: CatalogResultDTO) -> None:
        with transaction.atomic():
            master_map = self._seed_master_categories(dto.master_categories)
            sub_map = self._seed_sub_categories(dto.sub_categories, master_map)
            article_type_map = self._seed_article_types(dto.article_types, sub_map)
            base_colour_map = self._seed_base_colours(dto.base_colours)
            season_map = self._seed_seasons(dto.seasons)
            usage_type_map = self._seed_usage_types(dto.usage_types)
            images_map = self._build_images_map(dto.images)
            self._seed_products(
                dto.products,
                article_type_map,
                base_colour_map,
                season_map,
                usage_type_map,
                images_map,
            )

    def _seed_master_categories(
        self, items: Iterable[MasterCategoryDTO]
    ) -> Dict[str, MasterCategory]:
        instances = [MasterCategory(name=i.name) for i in items]
        MasterCategory.objects.bulk_create(
            instances, batch_size=self._batch_size, ignore_conflicts=True
        )

        names = [i.name for i in items]
        qs = MasterCategory.objects.filter(name__in=names)
        return {obj.name: obj for obj in qs}

    def _seed_sub_categories(
        self,
        items: Iterable[SubCategoryDTO],
        master_map: Dict[str, MasterCategory],
    ) -> Dict[str, SubCategory]:
        to_create: List[SubCategory] = []
        for dto in items:
            master = master_map.get(dto.master_category)
            if not master:
                continue
            to_create.append(SubCategory(master_category=master, name=dto.name))

        SubCategory.objects.bulk_create(
            to_create, batch_size=self._batch_size, ignore_conflicts=True
        )

        names = list({i.name for i in items})
        qs = SubCategory.objects.filter(name__in=names)
        return {obj.name: obj for obj in qs}

    def _seed_article_types(
        self,
        items: Iterable[ArticleTypeDTO],
        sub_map: Dict[str, SubCategory],
    ) -> Dict[str, ArticleType]:
        to_create: List[ArticleType] = []
        for dto in items:
            sub = sub_map.get(dto.sub_category)
            if not sub:
                continue
            to_create.append(ArticleType(sub_category=sub, name=dto.name))

        ArticleType.objects.bulk_create(
            to_create, batch_size=self._batch_size, ignore_conflicts=True
        )

        names = list({i.name for i in items})
        qs = ArticleType.objects.filter(name__in=names)
        return {obj.name: obj for obj in qs}

    def _seed_base_colours(
        self, items: Iterable[BaseColourDTO]
    ) -> Dict[str, BaseColour]:
        instances = [BaseColour(name=i.name) for i in items]
        BaseColour.objects.bulk_create(
            instances, batch_size=self._batch_size, ignore_conflicts=True
        )
        names = [i.name for i in items]
        qs = BaseColour.objects.filter(name__in=names)
        return {obj.name: obj for obj in qs}

    def _seed_seasons(self, items: Iterable[SeasonDTO]) -> Dict[str, Season]:
        instances = [Season(name=i.name) for i in items]
        Season.objects.bulk_create(
            instances, batch_size=self._batch_size, ignore_conflicts=True
        )
        names = [i.name for i in items]
        qs = Season.objects.filter(name__in=names)
        return {obj.name: obj for obj in qs}

    def _seed_usage_types(
        self, items: Iterable[UsageTypeDTO]
    ) -> Dict[str, UsageType]:
        instances = [UsageType(name=i.name) for i in items]
        UsageType.objects.bulk_create(
            instances, batch_size=self._batch_size, ignore_conflicts=True
        )
        names = [i.name for i in items]
        qs = UsageType.objects.filter(name__in=names)
        return {obj.name: obj for obj in qs}

    @staticmethod
    def _build_images_map(items: Iterable[ImageDTO]) -> Dict[int, str]:
        result: Dict[int, str] = {}
        for img in items:
            result.setdefault(img.product_id, img.image_url)
        return result

    def _seed_products(
        self,
        items: Iterable[ProductDTO],
        article_type_map: Dict[str, ArticleType],
        base_colour_map: Dict[str, BaseColour],
        season_map: Dict[str, Season],
        usage_type_map: Dict[str, UsageType],
        images_map: Dict[int, str],
    ) -> None:
        to_create: List[Product] = []
        for dto in tqdm(items, desc="Build Product instances"):
            article_type = article_type_map.get(dto.article_type)
            base_colour = base_colour_map.get(dto.base_colour) if dto.base_colour else None
            season = season_map.get(dto.season) if dto.season else None
            usage_type = usage_type_map.get(dto.usage) if dto.usage else None

            display = dto.product_display_name or ""
            slug = f"{slugify(display) or 'product'}-{dto.product_id}"

            to_create.append(
                Product(
                    product_id=dto.product_id,
                    gender=dto.gender,
                    year=dto.year,
                    product_display_name=dto.product_display_name,
                    image_url=images_map.get(dto.product_id),
                    slug=slug,
                    article_type=article_type,
                    base_colour=base_colour,
                    season=season,
                    usage_type=usage_type,
                )
            )

        for i in tqdm(range(0, len(to_create), self._batch_size), desc="Bulk insert Products"):
            batch = to_create[i : i + self._batch_size]
            Product.objects.bulk_create(batch, batch_size=self._batch_size, ignore_conflicts=True)
