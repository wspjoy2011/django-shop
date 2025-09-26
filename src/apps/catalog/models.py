from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django_extensions.db.fields import AutoSlugField

from apps.favorites.models import FavoriteItem, FavoriteCollection
from .choices import SeasonChoices, GenderChoices
from ..cart.models import CartItem

User = get_user_model()


class MasterCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            "catalog:product_list_by_master",
            kwargs={"master_slug": self.slug}
        )


class SubCategory(models.Model):
    master_category = models.ForeignKey(
        'MasterCategory',
        on_delete=models.RESTRICT,
        related_name='sub_categories',
        db_index=True
    )
    name = models.CharField(max_length=50)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    class Meta:
        unique_together = (('master_category', 'name'),)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            "catalog:product_list_by_sub",
            kwargs={
                "master_slug": self.master_category.slug,
                "sub_slug": self.slug,
            },
        )


class ArticleType(models.Model):
    sub_category = models.ForeignKey(
        'SubCategory',
        on_delete=models.RESTRICT,
        related_name='article_types',
        db_index=True
    )
    name = models.CharField(max_length=50)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    class Meta:
        unique_together = (('sub_category', 'name'),)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            "catalog:product_list_by_article",
            kwargs={
                "master_slug": self.sub_category.master_category.slug,
                "sub_slug": self.sub_category.slug,
                "article_slug": self.slug,
            },
        )


class BaseColour(models.Model):
    name = models.TextField(unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    def __str__(self):
        return self.name


class Season(models.Model):
    name = models.CharField(max_length=10, choices=SeasonChoices.choices, unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    def __str__(self):
        return self.name


class UsageType(models.Model):
    name = models.TextField(unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    product_id = models.IntegerField(unique=True)
    gender = models.CharField(max_length=10, choices=GenderChoices.choices)
    year = models.SmallIntegerField()
    product_display_name = models.TextField()
    image_url = models.TextField()
    slug = AutoSlugField(
        populate_from=['product_display_name', 'product_id'],
        unique=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ratings_sum = models.PositiveIntegerField(default=0)
    ratings_count = models.PositiveIntegerField(default=0, db_index=True)

    article_type = models.ForeignKey(
        'ArticleType',
        on_delete=models.RESTRICT,
        related_name='products',
        db_index=True
    )
    base_colour = models.ForeignKey(
        'BaseColour',
        on_delete=models.RESTRICT,
        related_name='products',
        db_index=True
    )
    season = models.ForeignKey(
        'Season',
        on_delete=models.RESTRICT,
        related_name='products',
        db_index=True,
    )
    usage_type = models.ForeignKey(
        'UsageType',
        on_delete=models.RESTRICT,
        related_name='products',
        db_index=True
    )

    rated_by = models.ManyToManyField(
        User,
        through='ratings.Rating',
        related_name='rated_products',
        through_fields=('product', 'user'),
        blank=True,
        db_index=True
    )
    liked_by = models.ManyToManyField(
        User,
        through='ratings.Like',
        related_name='liked_products',
        through_fields=('product', 'user'),
        blank=True,
        db_index=True
    )
    disliked_by = models.ManyToManyField(
        User,
        through='ratings.Dislike',
        related_name='disliked_products',
        through_fields=('product', 'user'),
        blank=True,
        db_index=True
    )

    class Meta:
        ordering = ['-year', '-updated_at', '-created_at', '-id']
        indexes = [
            models.Index(fields=['-year', '-updated_at', '-created_at', '-id'], name='idx_year_upd_cre_id_desc', ),

            models.Index(fields=['product_display_name', 'id'], name='idx_name_id_asc'),
            models.Index(fields=['-product_display_name', '-id'], name='idx_name_id_desc'),

            models.Index(fields=['year', 'id'], name='idx_year_id_asc'),
            models.Index(fields=['-year', '-id'], name='idx_year_id_desc'),

            models.Index(fields=['created_at', 'id'], name='idx_created_id_asc'),
            models.Index(fields=['-created_at', '-id'], name='idx_created_id_desc'),
        ]

    def __str__(self):
        return self.product_display_name or f'Product {self.product_id}'

    def get_absolute_url(self):
        return reverse('catalog:product_detail', kwargs={'slug': self.slug})

    def get_rating_stats(self):
        if self.ratings_count > 0:
            return {
                'avg_rating': self.ratings_sum / self.ratings_count,
                'ratings_count': self.ratings_count
            }
        return {'avg_rating': 0.0, 'ratings_count': 0}

    def get_likes_count(self):
        if hasattr(self, 'likes_list'):
            return len(self.likes_list)
        return 0

    def get_dislikes_count(self):
        if hasattr(self, 'dislikes_list'):
            return len(self.dislikes_list)
        return 0

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'likes_list'):
            return any(like.user_id == user.id for like in self.likes_list)

        return self.likes.filter(user=user).exists()

    def is_disliked_by(self, user):
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'dislikes_list'):
            return any(dislike.user_id == user.id for dislike in self.dislikes_list)

        return self.dislikes.filter(user=user).exists()

    def is_rated_by(self, user):
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'ratings_list'):
            return any(r.user_id == user.id for r in self.ratings_list)

        return self.ratings.filter(user=user).exists()

    def get_user_rating(self, user):
        if not user or not user.is_authenticated:
            return None

        if hasattr(self, 'ratings_list'):
            for r in self.ratings_list:
                if r.user_id == user.id:
                    return r.score
            return None

        obj = self.ratings.only('score').filter(user=user).first()
        return obj.score if obj else None

    def has_inventory(self):
        return hasattr(self, 'inventory')

    def get_inventory(self):
        if self.has_inventory():
            return self.inventory
        return None

    def get_price(self):
        inventory = self.get_inventory()
        if inventory:
            return inventory.format_current_price()
        return None

    def get_stock_status(self):
        inventory = self.get_inventory()
        if inventory:
            return {
                'in_stock': inventory.is_in_stock,
                'quantity': inventory.available_quantity,
                'is_active': inventory.is_active
            }
        return {
            'in_stock': False,
            'quantity': 0,
            'is_active': False
        }

    def is_available_for_purchase(self):
        inventory = self.get_inventory()
        return inventory and inventory.is_active and inventory.is_in_stock

    def is_in_favorites(self, user):
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'favorites_list'):
            return any(fav.collection.user_id == user.id for fav in self.favorites_list)

        return FavoriteItem.objects.filter(
            collection__user=user,
            product=self
        ).exists()

    def get_favorites_count(self):
        if hasattr(self, 'favorites_list'):
            return len(self.favorites_list)

        return FavoriteItem.objects.filter(product=self).count()

    def get_in_carts_users_count(self):
        if hasattr(self, 'cart_items_list'):
            user_ids = {item.cart.user_id for item in self.cart_items_list}
            return len(user_ids)
        return (
            CartItem.objects
            .filter(product=self)
            .values_list('cart__user_id', flat=True)
            .distinct()
            .count()
        )

    def is_in_cart_of(self, user):
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'cart_items_list'):
            return any(item.cart.user_id == user.id for item in self.cart_items_list)

        from apps.cart.models import CartItem
        return CartItem.objects.filter(product=self, cart__user=user).exists()
