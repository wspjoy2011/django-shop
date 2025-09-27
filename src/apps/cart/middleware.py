from django.http import HttpRequest, HttpResponse

from .cookies import CartCookieManager
from .resolver import CartResolver


class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        cart_token_value = CartCookieManager.get_token(request)
        request.cart = CartResolver.resolve(request, cart_token_value)

        response = self.get_response(request)

        if getattr(request, "_cart_token_to_delete", False):
            CartCookieManager.clear_token(response)

        new_token = getattr(request, "_cart_token_to_set", None)
        if new_token:
            CartCookieManager.set_token(response, new_token)

        return response
