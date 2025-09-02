from django import template

register = template.Library()


@register.filter
def humanize_number(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value

    if value < 1000:
        return str(int(value))
    elif value < 1000000:
        result = value / 1000
        if result == int(result):
            return f"{int(result)}K"
        else:
            return f"{result:.1f}K"
    elif value < 1000000000:
        result = value / 1000000
        if result == int(result):
            return f"{int(result)}M"
        else:
            return f"{result:.1f}M"
    else:
        result = value / 1000000000
        if result == int(result):
            return f"{int(result)}B"
        else:
            return f"{result:.1f}B"


@register.filter
def format_with_spaces(value):
    try:
        value = int(float(value))
        return f"{value:,}".replace(',', ' ')
    except (ValueError, TypeError):
        return value


@register.filter
def smart_number(value, format_type='auto'):
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        return value

    if format_type == 'humanize':
        return humanize_number(value)
    elif format_type == 'spaces':
        return format_with_spaces(value)
    else:
        if num_value >= 1000000:
            return humanize_number(value)
        elif num_value >= 10000:
            return format_with_spaces(value)
        else:
            return str(int(num_value))
