from django.shortcuts import render
from django.views import View

from apps.cart.types import CartHttpRequest


class CartDetailView(View):
    template_name = "pages/cart/detail.html"

    def get(self, request: CartHttpRequest, *args, **kwargs):
        return render(request, self.template_name)
