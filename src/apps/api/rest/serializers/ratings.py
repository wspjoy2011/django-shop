from rest_framework import serializers

from ..choices import RatingActionChoices


class RatingCreateUpdateRequestSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)

    def validate_score(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Score must be between 1 and 5')
        return value


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
