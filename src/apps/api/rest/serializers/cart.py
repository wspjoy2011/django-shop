from rest_framework import serializers

from ..choices import CartActionChoices


class CartToggleResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=CartActionChoices.ALL_CHOICES)
    in_cart = serializers.BooleanField()
    cart_count = serializers.IntegerField()


class CartSummarySerializer(serializers.Serializer):
    total_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_quantity = serializers.IntegerField()
    items_count = serializers.IntegerField()


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
