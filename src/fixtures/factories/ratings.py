import random

from django.contrib.auth import get_user_model
import factory

from apps.catalog.models import Product
from apps.ratings.models import Rating, Like, Dislike

User = get_user_model()


class RatingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Rating
        django_get_or_create = ('user', 'product')

    user = factory.SubFactory('fixtures.factories.users.UserFactory')
    product = factory.Iterator(Product.objects.all())
    score = factory.LazyFunction(lambda: random.choices(
        [1, 2, 3, 4, 5],
        weights=[5, 10, 20, 35, 30],
        k=1
    )[0])


class LikeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Like
        django_get_or_create = ('user', 'product')

    user = factory.SubFactory('fixtures.factories.users.UserFactory')
    product = factory.Iterator(Product.objects.all())


class DislikeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dislike
        django_get_or_create = ('user', 'product')

    user = factory.SubFactory('fixtures.factories.users.UserFactory')
    product = factory.Iterator(Product.objects.all())
