from rest_framework import serializers

from .choices import RatingActionChoices, FavoriteActionChoices


# ========== Rating System Request Serializers ==========

class RatingCreateUpdateRequestSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)

    def validate_score(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Score must be between 1 and 5')
        return value


# ========== Rating System Response Serializers ==========

class LikeToggleResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=RatingActionChoices.LIKE_CHOICES)
    likes_count = serializers.IntegerField()
    dislikes_count = serializers.IntegerField()


class DislikeToggleResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=RatingActionChoices.DISLIKE_CHOICES)
    likes_count = serializers.IntegerField()
    dislikes_count = serializers.IntegerField()


class RatingCreateUpdateResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[RatingActionChoices.RATED, RatingActionChoices.UPDATED])
    score = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    ratings_count = serializers.IntegerField()


class RatingDeleteResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[RatingActionChoices.REMOVED])
    avg_rating = serializers.FloatField()
    ratings_count = serializers.IntegerField()


# ========== Favorites System Request Serializers ==========

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


# ========== Favorites System Response Serializers ==========

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


# ========== Error Response Serializers ==========

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


class ValidationErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    errors = serializers.DictField()


class MessageErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
