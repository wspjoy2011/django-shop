from rest_framework import status

from apps.api.rest.permissions import IsCollectionOwnerPermission
from apps.api.rest.views.base import BaseAPIView


class FavoriteCollectionPermissionMixin(BaseAPIView):

    def check_owner_permission(self, request, collection):
        permission = IsCollectionOwnerPermission()

        if not permission.has_object_permission(request, self, collection):
            return self.return_message_error(
                'You do not have permission to reorder items in this collection.',
                status.HTTP_403_FORBIDDEN
            )
        return None
