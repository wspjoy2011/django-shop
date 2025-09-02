import hashlib

from django import template
from django.utils.encoding import force_bytes

register = template.Library()


def _gravatar_url_from_email(email: str, size: int = 100, default: str = "identicon") -> str:
    email_normalized = (email or "").strip().lower()
    email_hash = hashlib.md5(force_bytes(email_normalized)).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?s={int(size)}&d={default}"


@register.filter(name="avatar_url")
def avatar_url(email: str, size: int = 100) -> str:
    return _gravatar_url_from_email(email, size=size)
