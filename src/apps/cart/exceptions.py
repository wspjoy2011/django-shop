from django.core.exceptions import ValidationError


class CartBaseError(ValidationError):
    error_key: str = "cart_error"
    default_message: str = "Cart error"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)

    def __str__(self):
        return self.messages[0] if self.messages else self.default_message


class ProductUnavailableError(CartBaseError):
    error_key = "product_unavailable"
    default_message = "Product is not available."


class NotEnoughStockError(CartBaseError):
    error_key = "not_enough_stock"
    default_message = "Not enough stock available."


class CartItemNotFoundError(CartBaseError):
    error_key = "cart_item_not_found"
    default_message = "Cart item not found."
