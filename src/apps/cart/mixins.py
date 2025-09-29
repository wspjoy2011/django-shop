from django.db.models import Prefetch, F

from .models import Cart, CartItem
from .types import CartHttpRequest


class CartQuerysetMixin:
    request: CartHttpRequest

    @staticmethod
    def get_items_queryset():
        return (
            CartItem.objects
            .select_related(
                "product",
                "product__inventory",
                "product__inventory__currency",
            )
            .only(
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
            .order_by("-updated_at", "-created_at")
        )

    def get_available_items_queryset(self):
        return (
            self.get_items_queryset()
            .filter(
                product__inventory__is_active=True,
                product__inventory__stock_quantity__gt=F('product__inventory__reserved_quantity'),
            )
        )

    def get_cart_queryset(self):
        return (
            Cart.objects
            .filter(pk=self.request.cart.pk)
            .select_related("user", "token")
            .prefetch_related(
                Prefetch("items", queryset=self.get_items_queryset(), to_attr="items_list"),
                Prefetch("items", queryset=self.get_available_items_queryset(), to_attr="available_items_list"),
            )
        )

    def get_cart(self) -> Cart:
        return self.get_cart_queryset().get()
