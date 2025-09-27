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
    FavoriteCollectionItemsCountAPIView,
    FavoriteCollectionTotalValueAPIView
)

from .cart import CartToggleAPIView

__all__ = [
    # Cart views
    'CartToggleAPIView',

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
    'FavoriteCollectionItemsCountAPIView',
    'FavoriteCollectionTotalValueAPIView'
]
