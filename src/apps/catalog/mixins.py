from django.contrib import messages
from django.shortcuts import redirect
from django.views import View


class ProductAccessMixin(View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "You do not have permission to add/edit/delete products.")
            return redirect("catalog:home")
        return super().dispatch(request, *args, **kwargs)
