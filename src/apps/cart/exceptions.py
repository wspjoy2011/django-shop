from django.core.exceptions import ValidationError


class ProductUnavailableError(ValidationError):
    error_key = "product_unavailable"

    def __init__(self, message: str | None = None):
        super().__init__(message or "Product is not available.")


class NotEnoughStockError(ValidationError):
    error_key = "not_enough_stock"

    def __init__(self, message: str | None = None):
        super().__init__(message or "Not enough stock available.")


class CartItemNotFoundError(ValidationError):
    error_key = "cart_item_not_found"

    def __init__(self, message: str | None = None):
        super().__init__(message or "Cart item not found.")
