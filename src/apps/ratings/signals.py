from django.db.models import F, Sum, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Rating


@receiver(post_save, sender=Rating)
def rating_saved(sender, instance, created, **kwargs):
    product = instance.product

    if created:
        product.ratings_sum = F('ratings_sum') + instance.score
        product.ratings_count = F('ratings_count') + 1
        product.save(update_fields=['ratings_sum', 'ratings_count'])
    else:
        aggregates = Rating.objects.filter(product=product).aggregate(
            ratings_sum=Sum('score'),
            ratings_count=Count('id')
        )
        product.ratings_sum = aggregates['ratings_sum'] or 0
        product.ratings_count = aggregates['ratings_count'] or 0
        product.save(update_fields=['ratings_sum', 'ratings_count'])


@receiver(post_delete, sender=Rating)
def rating_deleted(sender, instance, **kwargs):
    product = instance.product
    product.ratings_sum = F('ratings_sum') - instance.score
    product.ratings_count = F('ratings_count') - 1
    product.save(update_fields=['ratings_sum', 'ratings_count'])
