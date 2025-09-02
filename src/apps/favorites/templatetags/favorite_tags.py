from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag('components/favorite_button.html', takes_context=True)
def favorite_button(context, product, size='normal', show_count=True):
    request = context['request']
    user = request.user

    in_favorites = product.is_in_favorites(user) if user.is_authenticated else False

    favorites_count = product.get_favorites_count()

    favorite_toggle_url = reverse('favorites:toggle', args=[product.pk])

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
