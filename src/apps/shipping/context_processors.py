from django.conf import settings


def google_places(request):
    return {'GOOGLE_PLACES_BROWSER_KEY': settings.GOOGLE_PLACES_BROWSER_KEY}
