from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework import status

from django.db import transaction

from apps.catalog.models import Product
from apps.favorites.models import FavoriteCollection, FavoriteItem

from .base import BaseAPIView
from ..serializers import (
    FavoriteToggleResponseSerializer,
    FavoriteCollectionCreateRequestSerializer,
    FavoriteCollectionCreateResponseSerializer,
    FavoriteCollectionSetDefaultResponseSerializer,
    MessageResponseSerializer
)
from ..choices import FavoriteActionChoices


class FavoriteToggleAPIView(BaseAPIView):

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            user_favorites_qs = FavoriteItem.objects.filter(
                collection__user=user,
                product=product
            )
            if user_favorites_qs.exists():
                user_favorites_qs.delete()
                action = FavoriteActionChoices.REMOVED
            else:
                default_collection, _ = FavoriteCollection.get_or_create_default(user)
                default_collection.add_product(product)
                action = FavoriteActionChoices.ADDED

        favorites_count = FavoriteItem.objects.filter(product=product).count()

        response_data = {
            'action': action,
            'favorites_count': favorites_count,
        }

        serializer = FavoriteToggleResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class FavoriteCollectionCreateAPIView(BaseAPIView):

    def post(self, request):
        request_serializer = FavoriteCollectionCreateRequestSerializer(data=request.data)

        if not request_serializer.is_valid():
            return self.return_validation_error(request_serializer.errors)

        validated_data = request_serializer.validated_data
        name = validated_data['name']
        description = validated_data['description']
        is_public = validated_data['is_public']
        is_default = validated_data['is_default']

        if FavoriteCollection.objects.filter(user=request.user, name=name).exists():
            return self.return_validation_error({
                'name': ['A collection with this name already exists']
            })

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

        return self.return_success_response(
            response_data,
            FavoriteCollectionCreateResponseSerializer,
            status.HTTP_201_CREATED
        )


class FavoriteCollectionSetDefaultAPIView(BaseAPIView):

    def post(self, request, collection_id):
        collection = FavoriteCollection.objects.filter(id=collection_id, user=request.user).first()

        if not collection:
            return self.return_message_error(
                'Collection is not found',
                status.HTTP_404_NOT_FOUND
            )

        if collection.is_default:
            return self.return_message_error(
                'This collection is already set as default',
                status.HTTP_200_OK
            )

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

        return self.return_success_response(
            response_data,
            FavoriteCollectionSetDefaultResponseSerializer,
            status.HTTP_200_OK
        )

class FavoriteCollectionDeleteView(BaseAPIView):

    def delete(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        collection = get_object_or_404(FavoriteCollection, pk=collection_id, user=request.user)

        if collection.is_default:
            return self.return_message_error(
                'You cannot delete your default collection.'
            )

        if collection.favorite_items.exists():
            return self.return_message_error(
                'Collection is not empty. Please clear the items first or use the clear endpoint.',
                status_code=status.HTTP_409_CONFLICT
            )

        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteCollectionClearView(BaseAPIView):

    def delete(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        collection = get_object_or_404(FavoriteCollection, pk=collection_id, user=request.user)

        items_deleted_count, _ = collection.favorite_items.all().delete()

        response_data = {
            'success': True,
            'message': f'{items_deleted_count} items have been cleared from the collection.'
        }
        return self.return_success_response(response_data, MessageResponseSerializer)
