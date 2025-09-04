from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag('components/favorite_button.html', takes_context=True)
def favorite_button(context, product, size='normal', show_count=True):
    request = context['request']
    user = request.user

    in_favorites = product.is_in_favorites(user) if user.is_authenticated else False

    favorites_count = product.get_favorites_count()

    favorite_toggle_url = reverse('api:product_favorite_toggle', args=[product.pk])

    size_classes = {
        'small': 'favorite-small',
        'normal': 'favorite-normal',
        'large': 'favorite-large'
    }

    return {
        'product': product,
        'in_favorites': in_favorites,
        'favorites_count': favorites_count,
        'show_count': show_count,
        'size_class': size_classes.get(size, 'favorite-normal'),
        'is_authenticated': user.is_authenticated,
        'favorite_toggle_url': favorite_toggle_url,
    }


@register.filter
def api_set_default_url(collection_id):
    return reverse('api:favorite_collection_set_default', args=[collection_id])


@register.simple_tag
def api_collection_create_url():
    return reverse('api:favorite_collection_create')
