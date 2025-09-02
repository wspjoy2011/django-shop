from django.urls import path

from . import views

app_name = "ratings"

urlpatterns = [
    path(
        'product/<int:product_id>/like/',
        views.LikeToggleView.as_view(),
        name='product_like_toggle'),
    path(
        'product/<int:product_id>/dislike/',
        views.DislikeToggleView.as_view(),
        name='product_dislike_toggle'),
    path(
        'product/<int:product_id>/rating/',
        views.RatingCreateUpdateView.as_view(),
        name='product_rating_create_update'),
    path(
        'product/<int:product_id>/rating/delete/',
        views.RatingDeleteView.as_view(),
        name='product_rating_delete'),
]
