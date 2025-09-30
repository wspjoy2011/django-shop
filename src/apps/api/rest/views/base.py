from abc import ABC, abstractmethod
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.db import transaction

from apps.catalog.models import Product
from apps.ratings.models import Like, Dislike
from ..serializers import ValidationErrorResponseSerializer, MessageResponseSerializer


class APIResponseMixin:

    def return_validation_error(self, errors, status_code=status.HTTP_400_BAD_REQUEST):
        error_data = {
            'success': False,
            'errors': errors
        }
        serializer = ValidationErrorResponseSerializer(data=error_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status_code)

    def return_message_error(self, message, status_code=status.HTTP_400_BAD_REQUEST, error_key: str | None = None):
        error_data = {
            "success": False,
            "message": message,
        }
        if error_key:
            error_data["error_key"] = error_key

        serializer = MessageResponseSerializer(data=error_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status_code)

    def return_success_response(self, data, serializer_class, status_code=status.HTTP_200_OK):
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status_code)


class BaseRatingToggleAPIView(APIView, APIResponseMixin, ABC):
    permission_classes = [IsAuthenticated]

    @abstractmethod
    def get_existing_instance(self, user, product):
        pass

    @abstractmethod
    def get_opposite_model_class(self):
        pass

    @abstractmethod
    def get_current_model_class(self):
        pass

    @abstractmethod
    def get_toggle_actions(self):
        pass

    @abstractmethod
    def get_response_serializer_class(self):
        pass

    def get_counts(self, product):
        likes_count = Like.objects.filter(product=product).count()
        dislikes_count = Dislike.objects.filter(product=product).count()
        return likes_count, dislikes_count

    def perform_toggle_logic(self, user, product):
        existing_instance = self.get_existing_instance(user, product)
        action_when_removed, action_when_added = self.get_toggle_actions()

        if existing_instance:
            existing_instance.delete()
            action = action_when_removed
        else:
            opposite_model_class = self.get_opposite_model_class()
            opposite_model_class.objects.filter(user=user, product=product).delete()

            current_model_class = self.get_current_model_class()
            current_model_class.objects.create(user=user, product=product)
            action = action_when_added

        return action

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            action = self.perform_toggle_logic(user, product)

        likes_count, dislikes_count = self.get_counts(product)

        response_data = {
            'action': action,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count,
        }

        serializer_class = self.get_response_serializer_class()
        serializer = serializer_class(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class BaseAPIView(APIView, APIResponseMixin):
    permission_classes = [IsAuthenticated]
