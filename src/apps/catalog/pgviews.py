from decimal import Decimal

from django.db import models
from django.db.models import Q
from django_pgviews import view as pg


class PriceRangesMV(pg.MaterializedView):
    """
    Materialized view providing min/max effective price per category scope.

    The view aggregates effective_price (sale_price if present, otherwise base_price)
    across the product hierarchy dimensions:
    - master category
    - subcategory
    - article type

    It exposes multiple specificity levels using GROUPING SETS so that callers can
    retrieve the most specific available range for a given context.
    """

    concurrent_index = 'master_slug, sub_slug, article_slug'

    sql = """
          WITH inv AS (SELECT mc.slug                                AS master_slug, \
                              sc.slug                                AS sub_slug, \
                              at.slug                                AS article_slug, \
                              COALESCE(pi.sale_price, pi.base_price) AS effective_price \
                       FROM catalog_product p \
                                JOIN inventories_productinventory pi ON pi.product_id = p.id \
                                JOIN catalog_articletype at ON at.id = p.article_type_id \
                                JOIN catalog_subcategory sc ON sc.id = at.sub_category_id \
                                JOIN catalog_mastercategory mc ON mc.id = sc.master_category_id)
          SELECT ROW_NUMBER() OVER (ORDER BY master_slug, sub_slug, article_slug) as id,
                 master_slug,
                 sub_slug,
                 article_slug,
                 MIN(effective_price)                                             AS min_price,
                 MAX(effective_price)                                             AS max_price,
                 ((master_slug IS NOT NULL)::int + (sub_slug IS NOT NULL)::int +
                  (article_slug IS NOT NULL)::int)                                AS specificity
          FROM inv
          GROUP BY GROUPING SETS (
              (),
              (master_slug),
              (master_slug, sub_slug),
              (master_slug, sub_slug, article_slug)
              ); \
          """

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    master_slug: models.CharField = models.CharField(max_length=255, null=True)
    sub_slug: models.CharField = models.CharField(max_length=255, null=True)
    article_slug: models.CharField = models.CharField(max_length=255, null=True)
    min_price: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2)
    max_price: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2)
    specificity: models.IntegerField = models.IntegerField()

    class Meta:
        managed = False
        app_label = 'catalog'
        db_table = 'mv_price_ranges'
        indexes = [
            models.Index(fields=['master_slug'], name='mv_pr_master_slug'),
            models.Index(fields=['master_slug', 'sub_slug'], name='mv_pr_master_sub_slug'),
            models.Index(fields=['master_slug', 'sub_slug', 'article_slug'], name='mv_pr_dim_slug_idx'),
        ]

    @staticmethod
    def get_for_context(
            master_slug: str | None = None,
            sub_slug: str | None = None,
            article_slug: str | None = None
    ) -> tuple[Decimal | None, Decimal | None]:
        """
        Return the most specific available price range for the given context.

        Resolution order:
        - (master, sub, article)
        - (master, sub)
        - (master)
        - ()

        Args:
            master_slug: Optional master category slug.
            sub_slug: Optional subcategory slug.
            article_slug: Optional article type slug.

        Returns:
            tuple[Decimal | None, Decimal | None]: (min_price, max_price) or (None, None) when absent.
        """
        query = PriceRangesMV.objects.filter(
            Q(master_slug__isnull=True) | Q(master_slug=master_slug),
            Q(sub_slug__isnull=True) | Q(sub_slug=sub_slug),
            Q(article_slug__isnull=True) | Q(article_slug=article_slug),
        ).order_by('-specificity').only('min_price', 'max_price')

        row = query.first()
        return (row.min_price, row.max_price) if row else (None, None)


class GenderFilterOptionsMV(pg.MaterializedView):
    """
    Materialized view exposing distinct gender options per category scope.

    The view groups products by master/sub/article dimensions and returns a list
    of unique gender values available for the requested context.
    """

    concurrent_index = 'id'

    sql = """
          SELECT ROW_NUMBER() OVER (ORDER BY mc.slug, sc.slug, at.slug, p.gender) as id,
                 mc.slug                                                          AS master_slug,
                 sc.slug                                                          AS sub_slug,
                 at.slug                                                          AS article_slug,
                 p.gender
          FROM catalog_product p
                   JOIN catalog_articletype at ON at.id = p.article_type_id
                   JOIN catalog_subcategory sc ON sc.id = at.sub_category_id
                   JOIN catalog_mastercategory mc ON mc.id = sc.master_category_id
          GROUP BY mc.slug,
                   sc.slug,
                   at.slug,
                   p.gender; \
          """
    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    master_slug: models.CharField = models.CharField(max_length=255, null=True)
    sub_slug: models.CharField = models.CharField(max_length=255, null=True)
    article_slug: models.CharField = models.CharField(max_length=255, null=True)
    gender: models.CharField = models.CharField(max_length=10)

    class Meta:
        managed = False
        app_label = 'catalog'
        db_table = 'mv_filter_options'
        indexes = [
            models.Index(fields=['master_slug', 'sub_slug', 'article_slug', 'gender'], name='mv_fo_idx'),
        ]

    @staticmethod
    def get_for_context(
            master_slug: str | None = None,
            sub_slug: str | None = None,
            article_slug: str | None = None
    ) -> list[str]:
        """
        Return distinct gender options for the most specific provided scope.

        Only one dimension is applied in priority order: article -> sub -> master.

        Args:
            master_slug: Optional master category slug.
            sub_slug: Optional subcategory slug.
            article_slug: Optional article type slug.

        Returns:
            list[str]: Sorted list of unique genders for the scope.
        """
        filters = Q()
        if article_slug:
            filters = Q(article_slug=article_slug)
        elif sub_slug:
            filters = Q(sub_slug=sub_slug)
        elif master_slug:
            filters = Q(master_slug=master_slug)

        return list(
            GenderFilterOptionsMV.objects.filter(filters)
            .values_list('gender', flat=True)
            .distinct()
            .order_by('gender')
        )
