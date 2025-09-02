from django import template

register = template.Library()


@register.filter
def is_active(request, names: str):
    """
    Return 'active' if current resolver url_name matches any of provided names.
    Supports qualified names with namespace like 'catalog:product_list'.

    Usage in templates:
      <a class="nav-link {{ request|is_active:'catalog:product_list' }}">Catalog</a>
      <a class="nav-link {{ request|is_active:'catalog:home, catalog:product_list' }}">...</a>
    """
    resolver_match = getattr(request, "resolver_match", None)
    if not resolver_match:
        return ""

    current_url_name = resolver_match.url_name or ""
    current_namespaces = resolver_match.namespaces or []
    current_app = getattr(resolver_match, "app_name", "")

    targets = [name.strip() for name in str(names).split(",") if name.strip()]
    for target in targets:
        if ":" in target:
            ns, name = target.split(":", 1)
            ns = ns.strip()
            name = name.strip()
            if current_url_name == name and (ns in current_namespaces or ns == current_app):
                return "active"
        else:
            if current_url_name == target:
                return "active"

    return ""
