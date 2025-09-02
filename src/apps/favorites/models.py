from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django_extensions.db.fields import AutoSlugField

User = get_user_model()


class FavoriteCollection(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_collections',
        db_index=True
    )
    name = models.CharField(
        max_length=255,
        default='My favorites',
        help_text="Name of the collection"
    )
    slug = AutoSlugField(
        populate_from=['user__username', 'name'],
        blank=True,
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the collection"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default collection for the user"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this collection is visible to other users"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    products = models.ManyToManyField(
        'catalog.Product',
        through='FavoriteItem',
        related_name='favorite_collections',
        blank=True,
        help_text="Products in this collection"
    )

    class Meta:
        unique_together = [('user', 'name')]
        ordering = ['is_default', '-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default'], name='idx_fav_coll_user_default'),
            models.Index(fields=['user', '-updated_at'], name='idx_fav_coll_user_updated'),
            models.Index(fields=['is_public', '-updated_at'], name='idx_fav_coll_public'),
            models.Index(fields=['user', 'slug'], name='idx_fav_coll_user_slug'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_default=True),
                name='unique_default_collection_per_user'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def get_absolute_url(self):
        return reverse('favorites:collection_detail', kwargs={
            'username': self.user.username,
            'slug': self.slug
        })

    def save(self, *args, **kwargs):
        if not self.pk and not FavoriteCollection.objects.filter(user=self.user).exists():
            self.is_default = True

        super().save(*args, **kwargs)

        if self.is_default:
            FavoriteCollection.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

    @property
    def items_count(self):
        return self.favorite_items.count()

    def add_product(self, product, position=None):
        if position is None:
            last_item = self.favorite_items.order_by('-position').first()
            position = (last_item.position + 1) if last_item else 1

        favorite_item, created = FavoriteItem.objects.get_or_create(
            collection=self,
            product=product,
            defaults={'position': position}
        )
        return favorite_item, created

    def remove_product(self, product):
        return FavoriteItem.objects.filter(
            collection=self,
            product=product
        ).delete()

    def has_product(self, product):
        return self.favorite_items.filter(product=product).exists()

    @classmethod
    def get_or_create_default(cls, user):
        collection, created = cls.objects.get_or_create(
            user=user,
            is_default=True,
            defaults={'name': 'My favorites'}
        )
        return collection, created


class FavoriteItem(models.Model):
    collection = models.ForeignKey(
        FavoriteCollection,
        on_delete=models.CASCADE,
        related_name='favorite_items',
        db_index=True
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='favorite_items',
        db_index=True
    )
    position = models.PositiveIntegerField(
        default=1,
        help_text="Position of item in the collection"
    )
    note = models.TextField(
        blank=True,
        help_text="Optional note about this favorite item"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('collection', 'product')]
        ordering = ['position', '-created_at']
        indexes = [
            models.Index(fields=['collection', 'position'], name='idx_fav_item_coll_pos'),
            models.Index(fields=['product', '-created_at'], name='idx_fav_item_prod_created'),
            models.Index(fields=['collection', '-created_at'], name='idx_fav_item_coll_created'),
        ]

    def __str__(self):
        return f"{self.collection.name} - {self.product.product_display_name}"

    def save(self, *args, **kwargs):
        if not self.position:
            last_item = FavoriteItem.objects.filter(
                collection=self.collection
            ).order_by('-position').first()
            self.position = (last_item.position + 1) if last_item else 1

        super().save(*args, **kwargs)
