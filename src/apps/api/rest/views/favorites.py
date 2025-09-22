from django.db.models import Q
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.response import Response
from rest_framework import status

from django.db import transaction

from apps.catalog.models import Product
from apps.favorites.mixins import FavoriteItemsQuerysetMixin
from apps.favorites.models import FavoriteCollection, FavoriteItem

from .base import BaseAPIView
from ..mixins import FavoriteCollectionPermissionMixin
from ..paginators import FavoriteItemsPagination
from ..permissions import IsOwnerOrPublicReadOnly, IsCollectionOwnerPermission
from ..serializers import (
    FavoriteToggleResponseSerializer,
    FavoriteCollectionCreateRequestSerializer,
    FavoriteCollectionCreateResponseSerializer,
    FavoriteCollectionSetDefaultResponseSerializer,
    MessageResponseSerializer,
    UserFavoritesCountResponseSerializer,
    FavoriteCollectionReorderRequestSerializer,
    FavoriteItemSerializer, FavoriteCollectionPrivacyToggleResponseSerializer, FavoriteItemsBulkDeleteRequestSerializer
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
            'absolute_url': collection.get_absolute_url()
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


class FavoriteCollectionClearView(FavoriteCollectionPermissionMixin, BaseAPIView):

    def delete(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        collection = get_object_or_404(FavoriteCollection, pk=collection_id)

        self.check_owner_permission(request, collection)

        items_deleted_count, _ = collection.favorite_items.all().delete()

        response_data = {
            'success': True,
            'message': f'{items_deleted_count} items have been cleared from the collection.'
        }
        return self.return_success_response(response_data, MessageResponseSerializer)


class UserFavoritesCountView(BaseAPIView):

    def get(self, request, *args, **kwargs):
        count = FavoriteItem.objects.filter(collection__user=request.user).count()

        return self.return_success_response(
            data={'count': count},
            serializer_class=UserFavoritesCountResponseSerializer,
            status_code=status.HTTP_200_OK
        )


class FavoriteCollectionReorderAPIView(FavoriteCollectionPermissionMixin, BaseAPIView):

    def post(self, request, collection_id):
        collection = get_object_or_404(FavoriteCollection, id=collection_id)

        self.check_owner_permission(request, collection)

        request_serializer = FavoriteCollectionReorderRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return self.return_validation_error(request_serializer.errors)

        items_data = request_serializer.validated_data['items']

        requested_item_ids, position_map = self._extract_items_data(items_data)

        existing_items, missing_ids = self._validate_items_exist(collection, requested_item_ids)
        if missing_ids:
            return self.return_validation_error({
                'items': [f'Items with IDs {list(missing_ids)} do not exist in this collection']
            })

        self._update_items_positions(existing_items, position_map)

        self._save_reorder_changes(collection, existing_items)

        response_data = {
            'success': True,
            'message': 'Items reordered successfully',
        }

        return self.return_success_response(
            response_data,
            MessageResponseSerializer,
            status.HTTP_200_OK
        )

    def _extract_items_data(self, items_data):
        requested_item_ids = []
        position_map = {}
        for item in items_data:
            item_id = item['item_id']
            requested_item_ids.append(item_id)
            position_map[item_id] = item['position']
        return requested_item_ids, position_map

    def _validate_items_exist(self, collection, requested_item_ids):
        existing_items = FavoriteItem.objects.filter(
            collection=collection,
            id__in=requested_item_ids
        )

        existing_item_ids = set(existing_items.values_list('id', flat=True))
        if len(existing_item_ids) != len(requested_item_ids):
            missing_ids = set(requested_item_ids) - existing_item_ids
            return None, missing_ids

        return existing_items, None

    def _update_items_positions(self, existing_items, position_map):
        for item in existing_items:
            item.position = position_map[item.id]

    def _save_reorder_changes(self, collection, existing_items):
        with transaction.atomic():
            FavoriteItem.objects.bulk_update(existing_items, ['position'])
            collection.save(update_fields=['updated_at'])


class FavoriteItemsListAPIView(FavoriteItemsQuerysetMixin, ListAPIView):
    serializer_class = FavoriteItemSerializer
    pagination_class = FavoriteItemsPagination
    permission_classes = [IsOwnerOrPublicReadOnly]

    def get_object(self):
        if hasattr(self, "_collection"):
            return self._collection

        collection_id = self.kwargs.get("collection_id")
        qs = FavoriteCollection.objects.filter(id=collection_id)

        if self.request.user.is_authenticated:
            qs = qs.filter(Q(user=self.request.user) | Q(is_public=True))
        else:
            qs = qs.filter(is_public=True)

        collection = get_object_or_404(qs)
        self.check_object_permissions(self.request, collection)

        self._collection = collection
        return self._collection

    def get_queryset(self):
        collection = self.get_object()
        return self.get_items_queryset(collection)


class FavoriteCollectionPrivacyToggleAPIView(FavoriteCollectionPermissionMixin, BaseAPIView):

    def post(self, request, collection_id):
        collection = get_object_or_404(FavoriteCollection, id=collection_id)

        self.check_owner_permission(request, collection)

        collection.is_public = not collection.is_public
        collection.save(update_fields=['is_public', 'updated_at'])

        response_data = {
            "id": collection.id,
            "is_public": collection.is_public
        }

        return self.return_success_response(
            response_data,
            FavoriteCollectionPrivacyToggleResponseSerializer,
            status.HTTP_201_CREATED
        )


class FavoriteItemsBulkDeleteAPIView(FavoriteCollectionPermissionMixin, BaseAPIView):

    def post(self, request, collection_id: int):
        collection = get_object_or_404(FavoriteCollection, id=collection_id)

        self.check_owner_permission(request, collection)

        serializer = FavoriteItemsBulkDeleteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item_ids = serializer.validated_data['item_ids']

        with transaction.atomic():
            (
                FavoriteItem.objects
                .filter(collection=collection, id__in=item_ids)
                .delete()
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
