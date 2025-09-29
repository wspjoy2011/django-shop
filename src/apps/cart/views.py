from django.shortcuts import render
from django.views import View

from .mixins import CartQuerysetMixin


class CartDetailView(CartQuerysetMixin, View):
    template_name = "pages/cart/detail.html"

    def get(self, request, *args, **kwargs):
        user_cart = self.get_cart()
        context = {"user_cart": user_cart}
        return render(request, self.template_name, context)
