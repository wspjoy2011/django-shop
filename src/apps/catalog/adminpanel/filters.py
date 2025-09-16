from django.contrib.admin import SimpleListFilter
from django.db.models import Min, Max, F, FloatField
from django.db.models.functions import Cast


class StockStatusFilter(SimpleListFilter):
    title = 'Stock Status'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return (
            ('in_stock', 'In Stock'),
            ('out_of_stock', 'Out of Stock'),
            ('low_stock', 'Low Stock (<10)'),
            ('no_inventory', 'No Inventory'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(inventory__stock_quantity__gt=0, inventory__is_active=True)
        elif self.value() == 'out_of_stock':
            return queryset.filter(inventory__stock_quantity=0)
        elif self.value() == 'low_stock':
            return queryset.filter(inventory__stock_quantity__gt=0, inventory__stock_quantity__lt=10)
        elif self.value() == 'no_inventory':
            return queryset.filter(inventory__isnull=True)
        return None


class YearFilter(SimpleListFilter):
    title = 'Year Range'
    parameter_name = 'year_range'

    def lookups(self, request, model_admin):
        year_range = model_admin.model.objects.aggregate(
            min_year=Min('year'), max_year=Max('year')
        )
        min_db_year = year_range.get('min_year')
        max_db_year = year_range.get('max_year')

        if not min_db_year or not max_db_year:
            return []

        ranges = []
        current_year = (max_db_year // 5) * 5
        while current_year >= min_db_year:
            start_range = current_year
            end_range = current_year + 4

            lookup_value = f"{start_range}_{end_range}"
            display_text = f"{start_range} - {end_range}"
            ranges.append((lookup_value, display_text))

            current_year -= 5

        return ranges

    def queryset(self, request, queryset):
        if self.value():
            try:
                start_year, end_year = map(int, self.value().split('_'))
                return queryset.filter(year__gte=start_year, year__lte=end_year)
            except (ValueError, TypeError):
                return queryset
        return queryset


class RatingFilter(SimpleListFilter):
    title = 'Rating Quality'
    parameter_name = 'rating_quality'

    def lookups(self, request, model_admin):
        return (
            ('excellent', '4.5+ stars'),
            ('good', '3.5-4.4 stars'),
            ('average', '2.5-3.4 stars'),
            ('poor', '< 2.5 stars'),
            ('unrated', 'No ratings'),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if value == 'unrated':
            return queryset.filter(ratings_count=0)

        if value in ('excellent', 'good', 'average', 'poor'):
            qs = queryset.exclude(ratings_count=0).annotate(
                avg_rating=Cast(F('ratings_sum'), FloatField()) / F('ratings_count')
            )

            if value == 'excellent':
                return qs.filter(avg_rating__gte=4.5)
            if value == 'good':
                return qs.filter(avg_rating__gte=3.5, avg_rating__lt=4.5)
            if value == 'average':
                return qs.filter(avg_rating__gte=2.5, avg_rating__lt=3.5)
            if value == 'poor':
                return qs.filter(avg_rating__lt=2.5)

        return queryset
