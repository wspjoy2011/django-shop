from django.conf import settings
from django.db import models
from django.db.models import Q


class Address(models.Model):
    formatted = models.CharField(max_length=512)
    country = models.CharField(max_length=2)
    region = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    postal_code = models.CharField(max_length=32)
    street = models.CharField(max_length=192)
    house = models.CharField(max_length=32)
    apartment = models.CharField(max_length=32, blank=True)
    place_id = models.CharField(max_length=128, unique=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='UserAddress',
        related_name='addresses',
    )

    class Meta:
        indexes = [
            models.Index(fields=['place_id']),
            models.Index(fields=['country', 'city']),
            models.Index(fields=['city', 'street']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'country', 'region', 'city', 'postal_code', 'street', 'house', 'apartment'
                ],
                name='uniq_address_components',
            )
        ]

    def __str__(self):
        return self.formatted or f'{self.street} {self.house}, {self.city}'


class UserAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    is_default = models.BooleanField(default=False)
    is_validated = models.BooleanField(default=False)
    label = models.CharField(max_length=64, default='Home address')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'address')]
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['user', 'is_validated']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_default=True),
                name='uniq_user_default_address',
            ),
            models.UniqueConstraint(
                fields=['user', 'label'],
                name='uniq_user_label',
            )
        ]

    def __str__(self):
        return f'{self.user_id}:{self.address_id}'
