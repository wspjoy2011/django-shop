from rest_framework import serializers

from ..choices import CartActionChoices


class CartToggleResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=CartActionChoices.ALL_CHOICES)
    in_cart = serializers.BooleanField()
    cart_count = serializers.IntegerField()


class CartSummarySerializer(serializers.Serializer):
    total_items = serializers.CharField()
    total_subtotal = serializers.CharField()
    total_discount = serializers.CharField()
    total_value = serializers.CharField()
    total_quantity = serializers.CharField()


class CartItemPriceSerializer(serializers.Serializer):
    current_price = serializers.CharField()
    base_price = serializers.CharField()
    sale_price = serializers.CharField(required=False, allow_null=True)
    discount_percentage = serializers.FloatField(required=False, allow_null=True)
    total_price = serializers.CharField()


class CartItemDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    price = CartItemPriceSerializer()
