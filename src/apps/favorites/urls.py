from django.urls import path
from . import views

app_name = 'favorites'

urlpatterns = [
    path(
        'collections/',
        views.FavoriteCollectionListView.as_view(),
        name='collection_list'
    ),
    path(
        'collections/<str:username>/<slug:collection_slug>/',
        views.FavoriteCollectionDetailView.as_view(),
         name='collection_detail'
    ),
]
