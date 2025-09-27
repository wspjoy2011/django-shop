from decimal import Decimal


def cart_summary(request):
    cart = getattr(request, "cart", None)

    if not cart:
        return {
            "cart_summary": {
                "total_value": Decimal("0.00"),
                "total_quantity": 0,
                "items_count": 0,
            }
        }

    return {
        "cart_summary": {
            "total_value": cart.total_value,
            "total_quantity": cart.total_quantity,
            "items_count": cart.items_count,
        }
    }
