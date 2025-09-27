from django.conf import settings
from django.http import HttpRequest, HttpResponse


class CartCookieManager:
    @staticmethod
    def get_token(request: HttpRequest) -> str | None:
        return request.COOKIES.get(settings.CART_COOKIE_NAME)

    @staticmethod
    def set_token(response: HttpResponse, token: str) -> None:
        response.set_cookie(
            key=settings.CART_COOKIE_NAME,
            value=token,
            max_age=settings.CART_COOKIE_AGE,
            secure=settings.CART_COOKIE_SECURE,
            httponly=settings.CART_COOKIE_HTTPONLY,
            samesite=settings.CART_COOKIE_SAMESITE
        )

    @staticmethod
    def clear_token(response: HttpResponse) -> None:
        response.delete_cookie(
            key=settings.CART_COOKIE_NAME,
            samesite=settings.CART_COOKIE_SAMESITE
        )
