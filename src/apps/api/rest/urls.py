from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
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
        'favorites/collections/<int:collection_id>/set-default/',
        views.FavoriteCollectionSetDefaultAPIView.as_view(),
        name='favorite_collection_set_default'),
    path(
        'favorites/collections/count/',
        views.UserFavoritesCountView.as_view(),
        name='user_favorites_count'),

]
