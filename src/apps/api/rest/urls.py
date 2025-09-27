from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    # Cart System APIs
    path(
        'products/<int:product_id>/cart/',
        views.CartToggleAPIView.as_view(),
        name='product_cart_toggle'
    ),
    path(
        "cart/summary/",
        views.CartSummaryAPIView.as_view(),
        name="cart_summary"
    ),

    # Rating System APIs
    path(
        'products/<int:product_id>/like/',
        views.LikeToggleAPIView.as_view(),
        name='product_like_toggle'),
    path(
        'products/<int:product_id>/dislike/',
        views.DislikeToggleAPIView.as_view(),
        name='product_dislike_toggle'),
    path(
        'product/<int:product_id>/rating/',
        views.RatingCreateUpdateDeleteAPIView.as_view(),
        name='product_rating_create_update'),

    # Favorites System APIs
    path(
        'products/<int:product_id>/favorite/',
        views.FavoriteToggleAPIView.as_view(),
        name='product_favorite_toggle'),
    path(
        'favorites/collections/',
        views.FavoriteCollectionCreateAPIView.as_view(),
        name='favorite_collection_create'),
    path(
        'favorites/collections/<int:collection_id>/',
        views.FavoriteCollectionDeleteView.as_view(),
        name='favorite_collection_delete'),
    path(
        'favorites/collections/<int:collection_id>/products/',
        views.FavoriteCollectionClearView.as_view(),
        name='favorite_collection_clear'),
    path(
        'favorites/collections/<int:collection_id>/items/',
        views.FavoriteItemsListAPIView.as_view(),
        name='favorite_collection_items'),
    path(
        'favorites/collections/<int:collection_id>/items/bulk-delete/',
        views.FavoriteItemsBulkDeleteAPIView.as_view(),
        name='favorite_collection_items_bulk_delete',
    ),
    path(
        'favorites/collections/<int:collection_id>/reorder/',
        views.FavoriteCollectionReorderAPIView.as_view(),
        name='favorite_collection_reorder'
    ),
    path(
        'favorites/collections/<int:collection_id>/set-default/',
        views.FavoriteCollectionSetDefaultAPIView.as_view(),
        name='favorite_collection_set_default'),
    path(
        'favorites/collections/count/',
        views.UserFavoritesCountView.as_view(),
        name='user_favorites_count'),
    path(
        'favorites/collections/<int:collection_id>/privacy-toggle/',
        views.FavoriteCollectionPrivacyToggleAPIView.as_view(),
        name='favorite_collection_privacy_toggle',
    ),
    path(
        'favorites/collections/<int:collection_id>/count/',
        views.FavoriteCollectionItemsCountAPIView.as_view(),
        name='favorite_collection_items_count',
    ),
    path(
        'favorites/collections/<int:collection_id>/total-value/',
        views.FavoriteCollectionTotalValueAPIView.as_view(),
        name='favorite_collection_total_value',
    ),
]
