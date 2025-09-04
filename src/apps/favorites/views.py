from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Count
from django.views.generic import ListView

from .models import FavoriteCollection, FavoriteItem


class FavoriteCollectionListView(LoginRequiredMixin, ListView):
    model = FavoriteCollection
    template_name = 'pages/favorites/collection/list.html'
    context_object_name = 'collections'
    paginate_by = 12

    def get_queryset(self):
        slider_items_qs = (
            FavoriteItem.objects
            .select_related(
                'product',
                'product__inventory',
                'product__inventory__currency',
            )
            .filter(product__image_url__isnull=False)
            .order_by('position')[:10]
        )

        return (
            FavoriteCollection.objects
            .filter(user=self.request.user)
            .select_related('user')
            .annotate(total_items_count=Count('favorite_items'))
            .prefetch_related(
                Prefetch(
                    'favorite_items',
                    queryset=slider_items_qs,
                    to_attr='slider_items'
                )
            )
            .order_by('-is_default', '-updated_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        total_collections = paginator.count if paginator else len(context.get('object_list', []))
        context['total_collections'] = total_collections
        context['has_collections'] = total_collections > 0
        return context
