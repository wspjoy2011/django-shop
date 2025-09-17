from .models import FavoriteItem


class FavoriteItemsQuerysetMixin:

    def get_items_queryset(self, collection):
        return (
            FavoriteItem.objects
            .filter(collection=collection)
            .select_related(
                'product',
                'product__inventory',
                'product__inventory__currency'
            )
            .only(
                'id',
                'position',
                'note',

                'product__product_display_name',
                'product__image_url',
                'product__slug',

                'product__inventory__is_active',
                'product__inventory__stock_quantity',
                'product__inventory__reserved_quantity',
                'product__inventory__base_price',
                'product__inventory__sale_price',
                'product__inventory__currency__symbol',
                'product__inventory__currency__code',
                'product__inventory__currency__decimals'
            )
            .order_by('position')
        )
