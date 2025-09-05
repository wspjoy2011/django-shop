from rest_framework import serializers

from ..choices import FavoriteActionChoices


class FavoriteCollectionCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')
    is_public = serializers.BooleanField(required=False, default=False)
    is_default = serializers.BooleanField(required=False, default=False)

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Collection name is required')
        return value.strip().capitalize()

    def validate_description(self, value):
        if value and len(value) > 1000:
            raise serializers.ValidationError('Description is too long')
        return value.strip() if value else ''


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
