from django.db.models import Prefetch, F

from .models import Cart, CartItem
from .query_fields import CART_ITEM_SELECT_RELATED, CART_ITEM_ONLY_FIELDS


class CartLoader:
    @staticmethod
    def get_items_queryset():
        return (
            CartItem.objects
            .select_related(*CART_ITEM_SELECT_RELATED)
            .only(*CART_ITEM_ONLY_FIELDS)
        )

    @classmethod
    def get_available_items_queryset(cls):
        return (
            cls.get_items_queryset()
            .filter(
                product__inventory__is_active=True,
                product__inventory__stock_quantity__gt=F("product__inventory__reserved_quantity"),
            )
        )

    @classmethod
    def get_cart_queryset(cls, cart_id: int):
        return (
            Cart.objects
            .filter(pk=cart_id)
            .select_related("user", "token")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=cls.get_items_queryset(),
                    to_attr="items_list"
                ),
                Prefetch(
                    "items",
                    queryset=cls.get_available_items_queryset(),
                    to_attr="available_items_list"
                ),
            )
        )

    @classmethod
    def get_cart(cls, cart_id: int) -> Cart:
        return cls.get_cart_queryset(cart_id).get()
