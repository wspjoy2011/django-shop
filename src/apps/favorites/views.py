import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.db import transaction, IntegrityError
from django.views.generic import ListView

from apps.catalog.models import Product
from .models import FavoriteCollection, FavoriteItem


class FavoriteToggleView(LoginRequiredMixin, View):

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            collection, _ = FavoriteCollection.get_or_create_default(user)

            existing_favorite = FavoriteItem.objects.filter(
                collection=collection,
                product=product
            ).first()

            if existing_favorite:
                existing_favorite.delete()
                action = 'removed'
            else:
                collection.add_product(product)
                action = 'added'

        favorites_count = FavoriteItem.objects.filter(product=product).count()

        return JsonResponse({
            'action': action,
            'favorites_count': favorites_count,
        })


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


class FavoriteCollectionCreateView(LoginRequiredMixin, View):

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'errors': {'non_field_errors': ['Invalid JSON data']}
            }, status=400)

        name = data.get('name', '').strip().capitalize()
        description = data.get('description', '').strip()
        is_public = data.get('is_public', False)
        is_default = data.get('is_default', False)

        errors = {}

        if not name:
            errors['name'] = ['Collection name is required']
        elif len(name) > 255:
            errors['name'] = ['Collection name cannot exceed 255 characters']

        if description and len(description) > 1000:
            errors['description'] = ['Description is too long']

        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)

        try:
            with transaction.atomic():
                if is_default:
                    FavoriteCollection.objects.filter(
                        user=request.user,
                        is_default=True
                    ).update(is_default=False)

                if not FavoriteCollection.objects.filter(user=request.user).exists():
                    is_default = True

                collection = FavoriteCollection.objects.create(
                    user=request.user,
                    name=name,
                    description=description,
                    is_public=is_public,
                    is_default=is_default
                )

        except IntegrityError as e:
            error_message = str(e).lower()
            if 'unique constraint' in error_message and 'name' in error_message:
                return JsonResponse({
                    'success': False,
                    'errors': {
                        'name': ['A collection with this name already exists']
                    }
                }, status=400)
            else:
                return JsonResponse({
                    'success': False,
                    'errors': {
                        'non_field_errors': ['Unable to create collection due to database constraint']
                    }
                }, status=400)

        response_data = {
            'success': True,
            'collection': {
                'id': collection.id,
                'name': collection.name,
                'description': collection.description,
                'slug': collection.slug,
                'is_default': collection.is_default,
                'is_public': collection.is_public,
                'total_items_count': 0,
                'created_at': collection.created_at.isoformat(),
                'updated_at': collection.updated_at.isoformat(),
                'formatted_updated_at': collection.updated_at.strftime('%b %d, %Y'),
                'slider_items': [],
                'absolute_url': ''
            }
        }

        return JsonResponse(response_data, status=201)
