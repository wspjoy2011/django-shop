from django.urls import path
from . import views

app_name = 'favorites'

urlpatterns = [
    path('toggle/<int:product_id>/', views.FavoriteToggleView.as_view(), name='toggle'),
    path('collections/', views.FavoriteCollectionListView.as_view(), name='collection_list'),
    path('collections/create/', views.FavoriteCollectionCreateView.as_view(), name='collection_create'),
]
