from django.urls import path
from . import views

app_name = "shipping"

urlpatterns = [
    path("addresses/", views.AddressDispatchView.as_view(), name="address_dispatch"),
    path("addresses/list/", views.AddressListView.as_view(), name="address_list"),
    path("addresses/create/", views.AddressCreateView.as_view(), name="address_create"),
]
