from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.db import transaction, IntegrityError

from apps.catalog.models import Product
from apps.ratings.models import Like, Dislike, Rating
from .serializers import (
    RatingCreateUpdateRequestSerializer,
    LikeToggleResponseSerializer,
    DislikeToggleResponseSerializer,
    RatingCreateUpdateResponseSerializer,
    RatingDeleteResponseSerializer,
    ErrorResponseSerializer, FavoriteToggleResponseSerializer, FavoriteCollectionCreateRequestSerializer,
    ValidationErrorResponseSerializer, FavoriteCollectionCreateResponseSerializer, MessageErrorResponseSerializer,
    FavoriteCollectionSetDefaultResponseSerializer
)
from .choices import RatingActionChoices, FavoriteActionChoices
from ...favorites.models import FavoriteCollection, FavoriteItem


class LikeToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            existing_like = Like.objects.filter(user=user, product=product).first()

            if existing_like:
                existing_like.delete()
                action = RatingActionChoices.UNLIKED
            else:
                Dislike.objects.filter(user=user, product=product).delete()
                Like.objects.create(user=user, product=product)
                action = RatingActionChoices.LIKED

        likes_count = Like.objects.filter(product=product).count()
        dislikes_count = Dislike.objects.filter(product=product).count()

        response_data = {
            'action': action,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count,
        }

        serializer = LikeToggleResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class DislikeToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            existing_dislike = Dislike.objects.filter(user=user, product=product).first()

            if existing_dislike:
                existing_dislike.delete()
                action = RatingActionChoices.UNDISLIKED
            else:
                Like.objects.filter(user=user, product=product).delete()
                Dislike.objects.create(user=user, product=product)
                action = RatingActionChoices.DISLIKED

        likes_count = Like.objects.filter(product=product).count()
        dislikes_count = Dislike.objects.filter(product=product).count()

        response_data = {
            'action': action,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count,
        }

        serializer = DislikeToggleResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RatingCreateUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        request_serializer = RatingCreateUpdateRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            error_serializer = ErrorResponseSerializer(data={'error': 'Invalid score value'})
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.validated_data, status=status.HTTP_400_BAD_REQUEST)

        score = request_serializer.validated_data['score']

        with transaction.atomic():
            rating, created = Rating.objects.update_or_create(
                user=user,
                product=product,
                defaults={'score': score}
            )

            action = RatingActionChoices.RATED if created else RatingActionChoices.UPDATED

        ratings = Rating.objects.filter(product=product)
        ratings_count = ratings.count()
        avg_rating = sum(r.score for r in ratings) / ratings_count if ratings_count > 0 else 0.0

        response_data = {
            'action': action,
            'score': score,
            'avg_rating': round(avg_rating, 1),
            'ratings_count': ratings_count,
        }

        serializer = RatingCreateUpdateResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    def delete(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            try:
                rating = Rating.objects.get(user=user, product=product)
                rating.delete()
                action = RatingActionChoices.REMOVED
            except Rating.DoesNotExist:
                error_serializer = ErrorResponseSerializer(data={'error': 'Rating not found'})
                error_serializer.is_valid(raise_exception=True)
                return Response(error_serializer.validated_data, status=status.HTTP_404_NOT_FOUND)

        ratings = Rating.objects.filter(product=product)
        ratings_count = ratings.count()
        avg_rating = sum(r.score for r in ratings) / ratings_count if ratings_count > 0 else 0.0

        response_data = {
            'action': action,
            'avg_rating': round(avg_rating, 1),
            'ratings_count': ratings_count,
        }

        serializer = RatingDeleteResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class FavoriteToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            collection, _ = FavoriteCollection.get_or_create_default(user)

            existing_favorite = FavoriteItem.objects.filter(
                collection=collection,
                product=product
            ).first()

            if existing_favorite:
                existing_favorite.delete()
                action = FavoriteActionChoices.REMOVED
            else:
                collection.add_product(product)
                action = FavoriteActionChoices.ADDED

        favorites_count = FavoriteItem.objects.filter(product=product).count()

        response_data = {
            'action': action,
            'favorites_count': favorites_count,
        }

        serializer = FavoriteToggleResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class FavoriteCollectionCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = FavoriteCollectionCreateRequestSerializer(data=request.data)

        if not request_serializer.is_valid():
            error_data = {
                'success': False,
                'errors': request_serializer.errors
            }
            serializer = ValidationErrorResponseSerializer(data=error_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_400_BAD_REQUEST)

        validated_data = request_serializer.validated_data
        name = validated_data['name']
        description = validated_data['description']
        is_public = validated_data['is_public']
        is_default = validated_data['is_default']

        if FavoriteCollection.objects.filter(user=request.user, name=name).exists():
            error_data = {
                'success': False,
                'errors': {
                    'name': ['A collection with this name already exists']
                }
            }
            serializer = ValidationErrorResponseSerializer(data=error_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                if is_default:
                    FavoriteCollection.objects.filter(
                        user=request.user,
                        is_default=True
                    ).update(is_default=False)

                if not FavoriteCollection.objects.filter(user=request.user).exists():
                    is_default = True

                collection = FavoriteCollection.objects.create(
                    user=request.user,
                    name=name,
                    description=description,
                    is_public=is_public,
                    is_default=is_default
                )

        except IntegrityError:
            error_data = {
                'success': False,
                'errors': {
                    'non_field_errors': ['Unable to create collection due to database constraint']
                }
            }
            serializer = ValidationErrorResponseSerializer(data=error_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_400_BAD_REQUEST)

        collection_data = {
            'id': collection.id,
            'name': collection.name,
            'description': collection.description,
            'slug': collection.slug,
            'is_default': collection.is_default,
            'is_public': collection.is_public,
            'total_items_count': 0,
            'created_at': collection.created_at.isoformat(),
            'updated_at': collection.updated_at.isoformat(),
            'formatted_updated_at': collection.updated_at.strftime('%b %d, %Y'),
            'slider_items': [],
            'absolute_url': ''
        }

        response_data = {
            'success': True,
            'collection': collection_data
        }

        serializer = FavoriteCollectionCreateResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_201_CREATED)


class FavoriteCollectionSetDefaultAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, collection_id):
        collection = FavoriteCollection.objects.filter(id=collection_id, user=request.user).first()

        if not collection:
            error_data = {
                'success': False,
                'message': 'Collection is not found'
            }
            serializer = MessageErrorResponseSerializer(data=error_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_404_NOT_FOUND)

        if collection.is_default:
            error_data = {
                'success': False,
                'message': 'This collection is already set as default'
            }
            serializer = MessageErrorResponseSerializer(data=error_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)

        with transaction.atomic():
            FavoriteCollection.objects.filter(
                user=request.user,
                is_default=True
            ).update(is_default=False)

            collection.is_default = True
            collection.save()

        response_data = {
            'success': True,
            'message': f'Collection "{collection.name}" is now set as default'
        }

        serializer = FavoriteCollectionSetDefaultResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
