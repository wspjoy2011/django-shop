from django.conf import settings

from .constants import EUROPEAN_COUNTRIES


def google_places(request):
    return {'GOOGLE_PLACES_BROWSER_KEY': settings.GOOGLE_PLACES_BROWSER_KEY}


def eu_countries(request):
    return {"EU_COUNTRY_CODES": EUROPEAN_COUNTRIES}
