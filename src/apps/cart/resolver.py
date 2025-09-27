from typing import Optional
from django.http import HttpRequest
from django.utils.crypto import get_random_string

from .models import Cart, CartToken

TOKEN_LENGTH = 32


class CartResolver:

    @staticmethod
    def resolve(request: HttpRequest, cart_token_value: Optional[str]) -> Cart:
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return Cart.get_or_create_for_user(user)

        if cart_token_value is not None:
            token = CartToken.objects.filter(token=cart_token_value).first()

            if token:
                if token.is_expired:
                    cart = Cart.objects.filter(token=token).first()

                    new_value = get_random_string(TOKEN_LENGTH)
                    new_token = CartToken.objects.create(token=new_value)

                    if cart:
                        cart.token = new_token
                        cart.save(update_fields=["token", "updated_at"])
                    else:
                        cart = Cart.get_or_create_for_token(new_token)

                    setattr(request, "_cart_token_to_delete", True)
                    setattr(request, "_cart_token_to_set", new_value)

                    token.delete()
                    return cart

                return Cart.get_or_create_for_token(token)

        new_value = get_random_string(TOKEN_LENGTH)
        new_token = CartToken.objects.create(token=new_value)
        cart = Cart.get_or_create_for_token(new_token)
        setattr(request, "_cart_token_to_set", new_value)
        return cart
