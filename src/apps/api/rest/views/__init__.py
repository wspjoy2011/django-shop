from .ratings import (
    LikeToggleAPIView,
    DislikeToggleAPIView,
    RatingCreateUpdateDeleteAPIView,
)

from .favorites import (
    FavoriteToggleAPIView,
    FavoriteCollectionCreateAPIView,
    FavoriteCollectionSetDefaultAPIView,
)

__all__ = [
    # Rating views
    'LikeToggleAPIView',
    'DislikeToggleAPIView',
    'RatingCreateUpdateDeleteAPIView',

    # Favorite views
    'FavoriteToggleAPIView',
    'FavoriteCollectionCreateAPIView',
    'FavoriteCollectionSetDefaultAPIView',
]
