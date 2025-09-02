from .models import FavoriteItem


def favorites_context(request):
    if not request.user.is_authenticated:
        return {'favorites_total_count': 0}

    favorites_total_count = FavoriteItem.objects.filter(
        collection__user=request.user
    ).count()

    return {
        'favorites_total_count': favorites_total_count,
    }
