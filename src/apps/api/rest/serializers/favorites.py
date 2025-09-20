from rest_framework import serializers

from apps.catalog.models import Product
from apps.favorites.models import FavoriteItem
from apps.inventories.models import ProductInventory, Currency
from ..choices import FavoriteActionChoices


class FavoriteCollectionCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')
    is_public = serializers.BooleanField(required=False, default=False)
    is_default = serializers.BooleanField(required=False, default=False)

    def validate_description(self, value):
        value = value.strip()

        if value and len(value) > 1000:
            raise serializers.ValidationError('Description is too long')
        return value


class FavoriteToggleResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=FavoriteActionChoices.TOGGLE_CHOICES)
    favorites_count = serializers.IntegerField()


class FavoriteCollectionDataSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, default='')
    slug = serializers.CharField()
    is_default = serializers.BooleanField()
    is_public = serializers.BooleanField()
    total_items_count = serializers.IntegerField()
    created_at = serializers.CharField()
    updated_at = serializers.CharField()
    formatted_updated_at = serializers.CharField()
    slider_items = serializers.ListField(default=list)
    absolute_url = serializers.CharField(allow_blank=True, default='')


class FavoriteCollectionCreateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    collection = FavoriteCollectionDataSerializer()


class FavoriteCollectionSetDefaultResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()


class UserFavoritesCountResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    count = serializers.IntegerField()


class FavoriteItemPositionSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    position = serializers.IntegerField(min_value=1)

    def validate_item_id(self, value):
        if value <= 0:
            raise serializers.ValidationError('Item ID must be a positive integer')
        return value


class FavoriteCollectionReorderRequestSerializer(serializers.Serializer):
    items = FavoriteItemPositionSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('At least one item is required')

        if len(value) > 100:
            raise serializers.ValidationError('Too many items. Maximum 100 items per request')

        item_ids = []
        positions = []
        for item in value:
            item_ids.append(item['item_id'])
            positions.append(item['position'])

        if len(item_ids) != len(set(item_ids)):
            raise serializers.ValidationError('Duplicate item IDs are not allowed')

        if len(positions) != len(set(positions)):
            raise serializers.ValidationError('Duplicate positions are not allowed')

        positions.sort()
        expected_positions = list(range(1, len(positions) + 1))
        if positions != expected_positions:
            raise serializers.ValidationError(
                f'Positions must be sequential starting from 1. '
                f'Expected: {expected_positions}, got: {positions}'
            )

        return value

    def validate(self, attrs):
        items = attrs.get('items', [])

        if not items:
            raise serializers.ValidationError('Items list cannot be empty')

        return attrs


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ("symbol", "code", "decimals")


class ProductInventorySerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    currency = CurrencySerializer(read_only=True)

    class Meta:
        model = ProductInventory
        fields = (
            "is_active",
            "stock_quantity",
            "reserved_quantity",
            "base_price",
            "sale_price",
            "currency",
            "available_quantity",
            "is_in_stock",
            "current_price",
            "is_on_sale",
            "discount_percentage",
        )

    def get_discount_percentage(self, obj):
        return obj.discount_percentage


class ProductInFavoriteSerializer(serializers.ModelSerializer):
    inventory = ProductInventorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "product_display_name",
            "image_url",
            "slug",
            "inventory",
        )


class FavoriteItemSerializer(serializers.ModelSerializer):
    product = ProductInFavoriteSerializer(read_only=True)

    class Meta:
        model = FavoriteItem
        fields = (
            "id",
            "position",
            "note",
            "product",
        )


class FavoriteCollectionPrivacyToggleResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    is_public = serializers.BooleanField()
