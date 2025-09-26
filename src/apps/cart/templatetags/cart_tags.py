from django import template

register = template.Library()

@register.inclusion_tag('components/cart_button.html', takes_context=True)
def cart_button(context, product, size='normal', show_count=True):
    request = context['request']
    user = request.user

    in_cart = product.is_in_cart_of(user) if user.is_authenticated else False
    carts_users_count = product.get_in_carts_users_count()

    cart_toggle_url = "#"

    size_classes = {
        'small': 'cart-small',
        'normal': 'cart-normal',
        'large': 'cart-large'
    }

    return {
        'product': product,
        'in_cart': in_cart,
        'carts_users_count': carts_users_count,
        'show_count': show_count,
        'size_class': size_classes.get(size, 'cart-normal'),
        'is_authenticated': user.is_authenticated,
        'cart_toggle_url': cart_toggle_url,
    }
