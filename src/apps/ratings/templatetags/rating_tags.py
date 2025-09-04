from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag('components/rating_stars.html', takes_context=True)
def rating_stars(
        context,
        rating,
        reviews_count,
        product,
        size='normal',
        show_text=True
):
    if not rating:
        rating = 0.0

    full_stars = int(rating)
    decimal_part = rating - full_stars
    has_half_star = decimal_part >= 0.5
    empty_stars = 5 - full_stars - (1 if has_half_star else 0)

    size_classes = {
        'small': 'rating-stars-small',
        'normal': 'rating-stars-normal',
        'large': 'rating-stars-large'
    }

    request = context['request']
    user = request.user
    user_rated = product.is_rated_by(user)
    user_score = product.get_user_rating(user)

    rating_url = reverse('api:product_rating_create_update', args=[product.pk])
    rating_delete_url = reverse('api:product_rating_create_update', args=[product.pk])

    return {
        'rating': rating,
        'reviews_count': reviews_count or 0,
        'full_stars': range(full_stars),
        'has_half_star': has_half_star,
        'empty_stars': range(empty_stars),
        'show_text': show_text,
        'size_class': size_classes.get(size, 'rating-stars-normal'),
        'rating_display': f"{rating:.1f}",
        'user_rated': user_rated,
        'user_score': user_score,
        'is_authenticated': user.is_authenticated,
        'rating_url': rating_url,
        'rating_delete_url': rating_delete_url,
    }


@register.inclusion_tag('components/likes_dislikes.html', takes_context=True)
def likes_dislikes(
        context,
        likes_count,
        dislikes_count,
        product,
        size='normal',
        show_counts=True
):
    likes_count = likes_count or 0
    dislikes_count = dislikes_count or 0

    size_classes = {
        'small': 'likes-dislikes-small',
        'normal': 'likes-dislikes-normal',
        'large': 'likes-dislikes-large'
    }

    extra_class = 'me-3' if likes_count == 0 and dislikes_count == 0 else ''

    like_url = reverse('api:product_like_toggle', args=[product.pk])
    dislike_url = reverse('api:product_dislike_toggle', args=[product.pk])

    request = context['request']
    user = request.user

    user_liked = product.is_liked_by(user)
    user_disliked = product.is_disliked_by(user)

    like_classes = 'liked-active' if user_liked else 'liked-inactive'
    dislike_classes = 'disliked-active' if user_disliked else 'disliked-inactive'

    return {
        'likes_count': likes_count,
        'dislikes_count': dislikes_count,
        'show_counts': show_counts,
        'size_class': size_classes.get(size, 'likes-dislikes-normal'),
        'extra_class': extra_class,
        'like_url': like_url,
        'dislike_url': dislike_url,
        'product_id': product.pk,
        'user': user,
        'user_liked': user_liked,
        'user_disliked': user_disliked,
        'like_classes': like_classes,
        'dislike_classes': dislike_classes,
    }
