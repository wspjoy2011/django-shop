from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect
from django.views import View

from .forms import AddressModelForm
from .models import UserAddress


class AddressView(LoginRequiredMixin, View):
    template_name = "pages/shipping/address.html"
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
        return redirect(request.path)
