from rest_framework.permissions import BasePermission


class IsCollectionOwnerPermission(BasePermission):

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and obj.user_id == request.user.id


class IsOwnerOrPublicReadOnly(BasePermission):

    def has_object_permission(self, request, view, obj):
        if obj.is_public:
            return True

        return request.user.is_authenticated and obj.user_id == request.user.id
