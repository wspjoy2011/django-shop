from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View


class AddressView(LoginRequiredMixin, View):
    template_name = "pages/shipping/address.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
