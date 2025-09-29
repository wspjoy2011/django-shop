from django.http import HttpRequest

from .models import Cart

class CartHttpRequest(HttpRequest):
    cart: Cart
