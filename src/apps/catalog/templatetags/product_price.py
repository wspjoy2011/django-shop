from django import template

register = template.Library()


@register.inclusion_tag('components/product_price.html')
def product_price(product, size='normal', show_currency=True):
    size_classes = {
        'small': 'product-price-small',
        'normal': 'product-price-normal',
        'large': 'product-price-large',
        'xl': 'product-price-xl'
    }

    has_inventory = bool(product.inventory)
    is_on_sale = has_inventory and product.inventory.is_on_sale if has_inventory else False

    price_data = {
        'has_inventory': has_inventory,
        'is_on_sale': is_on_sale,
    }

    if has_inventory:
        inventory = product.inventory
        price_data.update({
            'sale_price': inventory.format_sale_price if is_on_sale else None,
            'base_price': inventory.format_base_price if is_on_sale else None,
            'current_price': inventory.format_current_price if not is_on_sale else None,
            'discount_percentage': inventory.discount_percentage if is_on_sale else None,
        })
    else:
        price_data.update({
            'fallback_price': product.get_price(),
        })

    return {
        'product': product,
        'size_class': size_classes.get(size, 'product-price-normal'),
        'show_currency': show_currency,
        **price_data
    }
