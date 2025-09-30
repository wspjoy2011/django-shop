from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


class ValidationErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    errors = serializers.DictField()


class MessageResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    error_key = serializers.CharField(required=False, allow_null=True)
