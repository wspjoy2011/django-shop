from django.urls import path
from . import views

app_name = "shipping"

urlpatterns = [
    path("address/", views.AddressView.as_view(), name="address"),
]
