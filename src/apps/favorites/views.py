from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Count
from django.http import Http404
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
            .select_related(
                'product',
                'product__inventory',
                'product__inventory__currency',
            )
            .filter(product__image_url__isnull=False)
            .order_by('position')
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


class FavoriteCollectionDetailView(DetailView):
    model = FavoriteCollection
    template_name = 'pages/favorites/collection/detail.html'
    context_object_name = 'collection'

    def dispatch(self, request, *args, **kwargs):
        try:
            collection = self.get_object()
        except Http404:
            messages.warning(
                request,
                "Collection not found."
            )
            return redirect('catalog:home')

        if not collection.is_public:
            if not request.user.is_authenticated:
                messages.warning(
                    request,
                    "This collection is private. Please log in to view it."
                )
                return redirect('catalog:home')

            if collection.user != request.user:
                messages.warning(
                    request,
                    "You don't have access to this collection."
                )
                return redirect('catalog:home')

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        username = self.kwargs['username']
        collection_slug = self.kwargs['collection_slug']

        user = get_object_or_404(User, username=username)

        return get_object_or_404(
            FavoriteCollection.objects.select_related('user'),
            user=user,
            slug=collection_slug
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection = self.get_object()

        favorite_items = (
            FavoriteItem.objects
            .filter(collection=collection)
            .select_related('product')
            .order_by('position')
        )

        context['favorite_items'] = favorite_items
        context['items_count'] = favorite_items.count()

        return context
