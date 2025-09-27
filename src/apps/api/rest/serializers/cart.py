from rest_framework import serializers

from ..choices import CartActionChoices

class CartToggleResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=CartActionChoices.ALL_CHOICES)
    in_cart = serializers.BooleanField()
    cart_count = serializers.IntegerField()
