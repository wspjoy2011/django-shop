from django import template

register = template.Library()


@register.inclusion_tag('layout/form_field_errors.html')
def field_errors(field, show_icon=True):
    return {
        'field': field,
        'show_icon': show_icon,
    }


@register.inclusion_tag('layout/form_non_field_errors.html')
def non_field_errors(form, title="Form Errors"):
    return {
        'form': form,
        'title': title,
    }
