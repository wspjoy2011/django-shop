from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView

from .forms import AddressModelForm
from .models import UserAddress


class AddressDispatchView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.addresses.exists():
            return redirect("shipping:address_list")

        return redirect("shipping:address_create")


class AddressCreateView(LoginRequiredMixin, View):
    template_name = "pages/shipping/address/create.html"
    form_class = AddressModelForm

    def get(self, request, *args, **kwargs):
        address_form = self.form_class(user=request.user)
        return render(request, self.template_name, {"form": address_form})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        address_form = self.form_class(request.POST, user=request.user)
        if not address_form.is_valid():
            return render(request, self.template_name, {"form": address_form})

        try:
            address = address_form.save()
        except IntegrityError:
            message_text = "This address already exists."
            address_form.add_error(None, message_text)
            return render(request, self.template_name, {"form": address_form})

        is_validated = bool(address_form.cleaned_data.get("is_valid", False))
        is_default = bool(address_form.cleaned_data.get("is_default", False))
        label = address_form.cleaned_data.get("label", "Home address")

        user_address, created = UserAddress.objects.get_or_create(
            user=request.user,
            address=address,
            defaults={
                "is_validated": is_validated,
                "is_default": is_default,
                "label": label,
            },
        )

        fields_to_update = []
        if is_validated and not user_address.is_validated:
            user_address.is_validated = True
            fields_to_update.append("is_validated")
        if user_address.is_default != is_default:
            user_address.is_default = is_default
            fields_to_update.append("is_default")
        if label and user_address.label != label:
            user_address.label = label
            fields_to_update.append("label")
        if fields_to_update:
            user_address.save(update_fields=fields_to_update)

        messages.success(request, "Address has been added.")
        return redirect("shipping:address_list")


class AddressListView(LoginRequiredMixin, ListView):
    model = UserAddress
    template_name = "pages/shipping/address/list.html"
    context_object_name = "user_addresses"

    def get_queryset(self):
        return UserAddress.objects.select_related('address').filter(user=self.request.user)
