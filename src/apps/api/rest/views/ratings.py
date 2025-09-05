from rest_framework.generics import get_object_or_404
from rest_framework import status

from django.db import transaction

from apps.catalog.models import Product
from apps.ratings.models import Like, Dislike, Rating

from ..serializers import (
    RatingCreateUpdateRequestSerializer,
    LikeToggleResponseSerializer,
    DislikeToggleResponseSerializer,
    RatingCreateUpdateResponseSerializer,
    RatingDeleteResponseSerializer,
    ErrorResponseSerializer,
)
from .base import BaseRatingToggleAPIView, BaseAPIView
from ..choices import RatingActionChoices


class LikeToggleAPIView(BaseRatingToggleAPIView):

    def get_existing_instance(self, user, product):
        return Like.objects.filter(user=user, product=product).first()

    def get_opposite_model_class(self):
        return Dislike

    def get_current_model_class(self):
        return Like

    def get_toggle_actions(self):
        return RatingActionChoices.UNLIKED, RatingActionChoices.LIKED

    def get_response_serializer_class(self):
        return LikeToggleResponseSerializer


class DislikeToggleAPIView(BaseRatingToggleAPIView):

    def get_existing_instance(self, user, product):
        return Dislike.objects.filter(user=user, product=product).first()

    def get_opposite_model_class(self):
        return Like

    def get_current_model_class(self):
        return Dislike

    def get_toggle_actions(self):
        return RatingActionChoices.UNDISLIKED, RatingActionChoices.DISLIKED

    def get_response_serializer_class(self):
        return DislikeToggleResponseSerializer


class RatingCreateUpdateDeleteAPIView(BaseAPIView):

    def get_rating_stats(self, product):
        ratings = Rating.objects.filter(product=product)
        ratings_count = ratings.count()

        if ratings_count > 0:
            avg_rating = sum(r.score for r in ratings) / ratings_count
            avg_rating = round(avg_rating, 1)
        else:
            avg_rating = 0.0

        return {
            'avg_rating': avg_rating,
            'ratings_count': ratings_count
        }

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        request_serializer = RatingCreateUpdateRequestSerializer(data=request.data)

        if not request_serializer.is_valid():
            return self.return_success_response(
                {'error': 'Invalid score value'},
                ErrorResponseSerializer,
                status.HTTP_400_BAD_REQUEST
            )

        score = request_serializer.validated_data['score']

        with transaction.atomic():
            rating, created = Rating.objects.update_or_create(
                user=user,
                product=product,
                defaults={'score': score}
            )

            action = RatingActionChoices.RATED if created else RatingActionChoices.UPDATED

        rating_stats = self.get_rating_stats(product)

        response_data = {
            'action': action,
            'score': score,
            **rating_stats
        }

        return self.return_success_response(
            response_data,
            RatingCreateUpdateResponseSerializer,
            status.HTTP_200_OK
        )

    def delete(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            try:
                rating = Rating.objects.get(user=user, product=product)
                rating.delete()
                action = RatingActionChoices.REMOVED
            except Rating.DoesNotExist:
                return self.return_success_response(
                    {'error': 'Rating not found'},
                    ErrorResponseSerializer,
                    status.HTTP_404_NOT_FOUND
                )

        rating_stats = self.get_rating_stats(product)

        response_data = {
            'action': action,
            **rating_stats
        }

        return self.return_success_response(
            response_data,
            RatingDeleteResponseSerializer,
            status.HTTP_200_OK
        )
