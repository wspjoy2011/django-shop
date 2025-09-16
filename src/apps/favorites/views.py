from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Count
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView

from .models import FavoriteCollection, FavoriteItem

User = get_user_model()


class FavoriteCollectionListView(LoginRequiredMixin, ListView):
    model = FavoriteCollection
    template_name = 'pages/favorites/collection/list.html'
    context_object_name = 'collections'
    paginate_by = 12

    def get_queryset(self):
        slider_items_qs = (
            FavoriteItem.objects
            .filter(product__image_url__isnull=False)
            .select_related(
                'product',
                'product__inventory__currency'
            )
            .only(
                'id',
                'collection_id',
                'position',

                'product__image_url',
                'product__product_display_name',

                'product__inventory__base_price',
                'product__inventory__sale_price',

                'product__inventory__currency__symbol',
                'product__inventory__currency__code',
                'product__inventory__currency__decimals',
            )
            .order_by('position')
        )

        return (
            FavoriteCollection.objects
            .filter(user=self.request.user)
            .select_related('user')
            .only(
                'id',
                'name',
                'slug',
                'is_default',
                'updated_at',

                'user__username'
            )
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


class FavoriteCollectionDetailView(DetailView):
    model = FavoriteCollection
    template_name = 'pages/favorites/collection/detail.html'
    context_object_name = 'collection'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        collection = self.object

        if not collection.is_public:
            if not request.user.is_authenticated:
                messages.warning(
                    request,
                    "This collection is private. Please log in to view it."
                )
                return redirect('catalog:home')
            if request.user != collection.user:
                messages.warning(
                    request,
                    "You don't have access to this collection."
                )
                return redirect('catalog:home')

        return response

    def get_object(self, queryset=None):
        queryset = FavoriteCollection.objects.select_related('user').only(
            'id', 'name', 'description', 'is_public', 'slug', 'user__username'
        )

        return get_object_or_404(
            queryset,
            user__username=self.kwargs['username'],
            slug=self.kwargs['collection_slug']
        )

    def get_items_queryset(self, collection):
        return (
            FavoriteItem.objects
            .filter(collection=collection)
            .select_related(
                'product',
                'product__inventory',
                'product__inventory__currency'
            )
            .only(
                'id',
                'position',
                'note',

                'product__product_display_name',
                'product__image_url',
                'product__slug',

                'product__inventory__is_active',
                'product__inventory__stock_quantity',
                'product__inventory__reserved_quantity',
                'product__inventory__base_price',
                'product__inventory__sale_price',
                'product__inventory__currency__symbol',
                'product__inventory__currency__code',
                'product__inventory__currency__decimals'
            )
            .order_by('position')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection = self.object

        favorite_items_qs = self.get_items_queryset(collection)

        favorite_items_list = list(favorite_items_qs)

        context['favorite_items'] = favorite_items_list
        context['items_count'] = len(favorite_items_list)

        return context
