from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny

from apps.api.rest.choices import CartActionChoices
from apps.api.rest.serializers import CartToggleResponseSerializer
from apps.api.rest.views.base import BaseAPIView
from apps.catalog.models import Product


class CartToggleAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        cart = request.cart

        if cart.has_product(product):
            cart.remove_product(product)
            action = CartActionChoices.REMOVED
            in_cart = False
        else:
            cart.add_product(product, quantity=1)
            action = CartActionChoices.ADDED
            in_cart = True

        cart_count = cart.users_with_product_count(product)

        data = {
            "action": action,
            "in_cart": in_cart,
            "cart_count": cart_count,
        }
        return self.return_success_response(
            data=data,
            serializer_class=CartToggleResponseSerializer,
            status_code=status.HTTP_200_OK,
        )
