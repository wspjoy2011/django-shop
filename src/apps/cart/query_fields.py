CART_ITEM_SELECT_RELATED = (
    "product",
    "product__inventory",
    "product__inventory__currency",
)

CART_ITEM_ONLY_FIELDS = (
    "id",
    "quantity",
    "updated_at",
    "created_at",
    "cart_id",

    "product__id",
    "product__slug",
    "product__image_url",
    "product__product_display_name",
    "product__product_id",
    "product__year",

    "product__inventory__id",
    "product__inventory__is_active",
    "product__inventory__stock_quantity",
    "product__inventory__reserved_quantity",
    "product__inventory__base_price",
    "product__inventory__sale_price",
    "product__inventory__currency__code",
    "product__inventory__currency__symbol",
    "product__inventory__currency__decimals",
)
