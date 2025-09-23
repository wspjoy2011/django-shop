from .ratings import (
    LikeToggleAPIView,
    DislikeToggleAPIView,
    RatingCreateUpdateDeleteAPIView,
)

from .favorites import (
    FavoriteToggleAPIView,
    FavoriteCollectionCreateAPIView,
    FavoriteCollectionSetDefaultAPIView,
    FavoriteCollectionDeleteView,
    FavoriteCollectionClearView,
    UserFavoritesCountView,
    FavoriteCollectionReorderAPIView,
    FavoriteItemsListAPIView,
    FavoriteCollectionPrivacyToggleAPIView,
    FavoriteItemsBulkDeleteAPIView,
    FavoriteCollectionItemsCountAPIView
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
    'FavoriteCollectionDeleteView',
    'FavoriteCollectionClearView',
    'UserFavoritesCountView',
    'FavoriteCollectionReorderAPIView',
    'FavoriteItemsListAPIView',
    'FavoriteCollectionPrivacyToggleAPIView',
    'FavoriteItemsBulkDeleteAPIView',
    'FavoriteCollectionItemsCountAPIView'
]
