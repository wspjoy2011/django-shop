from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny

from apps.api.rest.choices import CartActionChoices
from apps.api.rest.serializers import CartToggleResponseSerializer, CartSummarySerializer, \
    CartItemDetailSerializer
from apps.api.rest.views.base import BaseAPIView
from apps.cart.exceptions import ProductUnavailableError, NotEnoughStockError, CartItemNotFoundError

from apps.cart.types import CartHttpRequest
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


class CartSummaryAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request: CartHttpRequest):
        cart = request.cart
        data = cart.get_summary()
        return self.return_success_response(
            data=data,
            serializer_class=CartSummarySerializer,
            status_code=200,
        )


class CartItemIncreaseAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request, product_id: int, *args, **kwargs):
        product = get_object_or_404(Product, pk=product_id)

        try:
            item = request.cart.add_product(product=product, quantity=1)
        except ProductUnavailableError as e:
            return self.return_message_error(
                message=str(e),
                error_key=e.error_key,
                status_code=status.HTTP_409_CONFLICT,
            )
        except NotEnoughStockError as e:
            return self.return_message_error(
                message=str(e),
                error_key=e.error_key,
                status_code=status.HTTP_409_CONFLICT,
            )

        payload = {
            "id": item.pk,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": {
                **product.get_price_info(),
                "total_price": str(item.format_line_total),
            },
        }
        return self.return_success_response(
            data=payload,
            serializer_class=CartItemDetailSerializer,
            status_code=status.HTTP_200_OK,
        )


class CartItemDecreaseAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request, product_id: int, *args, **kwargs):
        product = get_object_or_404(Product, pk=product_id)

        try:
            item = request.cart.decrease_product(product=product, step=1)
        except CartItemNotFoundError as e:
            return self.return_message_error(
                message=str(e),
                error_key=e.error_key,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except NotEnoughStockError as e:
            return self.return_message_error(
                message=str(e),
                error_key=e.error_key,
                status_code=status.HTTP_409_CONFLICT,
            )

        payload = {
            "id": item.pk,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": {
                **product.get_price_info(),
                "total_price": str(item.line_total),
            },
        }
        return self.return_success_response(
            data=payload,
            serializer_class=CartItemDetailSerializer,
            status_code=status.HTTP_200_OK,
        )
