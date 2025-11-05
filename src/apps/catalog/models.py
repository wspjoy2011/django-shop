from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import ManyToManyField
from django.urls import reverse
from django_extensions.db.fields import AutoSlugField

from apps.favorites.models import FavoriteItem, FavoriteCollection
from .choices import SeasonChoices, GenderChoices
from .protocols import SupportsUserAuth
from ..cart.models import CartItem, Cart
from ..inventories.models import ProductInventory

User = get_user_model()


class MasterCategory(models.Model):
    """
    Represents the top-level product category in the catalog hierarchy,
    serving as a parent for subcategories (e.g., "Clothing", "Footwear", "Accessories").
    """

    name = models.CharField(max_length=50, unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        """
        Return the absolute URL for the product list filtered by this master category.

        Returns:
            str: The URL path to the product list view corresponding to this master category.
        """
        return reverse(
            "catalog:product_list_by_master",
            kwargs={"master_slug": self.slug}
        )


class SubCategory(models.Model):
    """
    Represents a subcategory within a master category, providing
    a more specific grouping of related product types.
    For example, "Footwear" may include subcategories like "Sneakers" or "Boots".
    """

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

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        """
        Return the absolute URL for the product list filtered by this subcategory.

        Returns:
            str: The URL path to the product list view corresponding to this subcategory.
        """
        return reverse(
            "catalog:product_list_by_sub",
            kwargs={
                "master_slug": self.master_category.slug,
                "sub_slug": self.slug,
            },
        )


class ArticleType(models.Model):
    """
    Represents a specific type of product within a subcategory,
    defining a more detailed classification level (e.g., jackets, trousers, sneakers)
    under a broader subcategory of the catalog.
    """

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

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        """
        Return the absolute URL for the product list filtered by this article type.

        Returns:
            str: The URL path to the product list view corresponding to this article type.
        """
        return reverse(
            "catalog:product_list_by_article",
            kwargs={
                "master_slug": self.sub_category.master_category.slug,
                "sub_slug": self.sub_category.slug,
                "article_slug": self.slug,
            },
        )


class BaseColour(models.Model):
    """
    Represents a base color category for products (e.g., red, blue, black),
    defining the primary color attribute used for product classification.
    """

    name = models.TextField(unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    def __str__(self) -> str:
        return self.name


class Season(models.Model):
    """
    Represents a product season category (e.g., summer, winter, spring, autumn),
    indicating for which season the product is designed.
    """

    name = models.CharField(max_length=10, choices=SeasonChoices.choices, unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    def __str__(self) -> str:
        return self.name


class UsageType(models.Model):
    """
    Represents a product usage category (e.g., casual, formal, sports),
    defining the context or intended purpose of a product.
    """

    name = models.TextField(unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, blank=True)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """
    Represents a product in the catalog with its descriptive attributes,
    inventory information, pricing, user interactions (ratings, likes, favorites),
    and cart relationships.
    """

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

    rated_by: ManyToManyField = models.ManyToManyField(
        User,
        through='ratings.Rating',
        related_name='rated_products',
        through_fields=('product', 'user'),
        blank=True,
        db_index=True
    )
    liked_by: ManyToManyField = models.ManyToManyField(
        User,
        through='ratings.Like',
        related_name='liked_products',
        through_fields=('product', 'user'),
        blank=True,
        db_index=True
    )
    disliked_by: ManyToManyField = models.ManyToManyField(
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

    def __str__(self) -> str:
        return self.product_display_name or f'Product {self.product_id}'

    def get_absolute_url(self) -> str:
        """
        Return the absolute URL for this product detail page.

        Returns:
            str: The URL path to the product detail view.
        """
        return reverse('catalog:product_detail', kwargs={'slug': self.slug})

    def get_rating_stats(self) -> dict[str, float | int]:
        """
        Retrieve aggregated rating statistics for the product.

        Returns:
            dict[str, float | int]: A dictionary containing rating statistics with the following keys:
                - "avg_rating": The average rating value, or 0.0 if no ratings exist.
                - "ratings_count": The total number of ratings for the product.
        """
        if self.ratings_count > 0:
            return {
                'avg_rating': self.ratings_sum / self.ratings_count,
                'ratings_count': self.ratings_count
            }
        return {'avg_rating': 0.0, 'ratings_count': 0}

    def get_likes_count(self) -> int:
        """
        Return the number of likes associated with this product.

        Returns:
            int: Total count of likes for the product, or 0 if unavailable.
        """
        if hasattr(self, 'likes_list'):
            return len(self.likes_list)
        return 0

    def get_dislikes_count(self) -> int:
        """
        Return the number of dislikes associated with this product.

        Returns:
            int: Total count of dislikes for the product, or 0 if unavailable.
        """
        if hasattr(self, 'dislikes_list'):
            return len(self.dislikes_list)
        return 0

    def is_liked_by(self, user: SupportsUserAuth) -> bool:
        """
        Check whether the specified user has liked this product.

        Args:
            user (SupportsUserAuth): The user to check likes for.

        Returns:
            bool: True if the user has liked the product, False otherwise.
        """
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'likes_list'):
            return any(like.user_id == user.id for like in self.likes_list)

        return self.likes.filter(user_id=user.id).exists()

    def is_disliked_by(self, user: SupportsUserAuth) -> bool:
        """
        Check whether the specified user has disliked this product.

        Args:
            user (SupportsUserAuth): The user to check dislikes for.

        Returns:
            bool: True if the user has disliked the product, False otherwise.
        """
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'dislikes_list'):
            return any(dislike.user_id == user.id for dislike in self.dislikes_list)

        return self.dislikes.filter(user_id=user.id).exists()

    def is_rated_by(self, user: SupportsUserAuth) -> bool:
        """
        Check whether the specified user has rated this product.

        Args:
            user (SupportsUserAuth): The user to check ratings for.

        Returns:
            bool: True if the user has rated the product, False otherwise.
        """
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'ratings_list'):
            return any(rating.user_id == user.id for rating in self.ratings_list)

        return self.ratings.filter(user_id=user.id).exists()

    def get_user_rating(self, user: SupportsUserAuth) -> Optional[int]:
        """
        Return the rating score given by the specified user for this product.

        Args:
            user (SupportsUserAuth): The user whose rating is being retrieved.

        Returns:
            Optional[int]: The user's rating score if it exists, otherwise None.
        """
        if not user or not user.is_authenticated:
            return None

        if hasattr(self, 'ratings_list'):
            for rating in self.ratings_list:
                if rating.user_id == user.id:
                    return int(rating.score)
            return None

        obj = self.ratings.only('score').filter(user_id=user.id).first()
        return int(obj.score) if obj else None

    def has_inventory(self) -> bool:
        """
        Check whether the product has an associated inventory instance.

        Returns:
            bool: True if the product has an inventory relation, False otherwise.
        """
        return hasattr(self, 'inventory')

    def get_inventory(self) -> Optional[ProductInventory]:
        """
        Retrieve the inventory instance associated with this product, if available.

        Returns:
            Optional[ProductInventory]: The related inventory object if it exists, otherwise None.
        """
        if self.has_inventory():
            return self.inventory
        return None

    def get_price(self) -> Optional[str]:
        """
        Return the formatted current price of the product.

        Returns:
            Optional[str]: The formatted current price if inventory exists, otherwise None.
        """
        inventory = self.get_inventory()
        if inventory:
            return inventory.format_current_price()
        return None

    def get_stock_status(self) -> dict[str, bool | int]:
        """
        Retrieve the current stock status of the product.

        Returns:
            dict[str, bool | int]: A dictionary containing stock-related information with the following keys:
                - "in_stock": Whether the product is currently in stock.
                - "quantity": The available quantity of the product.
                - "is_active": Whether the inventory record is active.
        """
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

    def get_price_info(self) -> dict[str, object]:
        """
        Retrieve formatted pricing information for the product.

        Returns:
            dict[str, object]: A dictionary containing formatted price details with the following keys:
                - "current_price": Formatted current price or None if unavailable.
                - "base_price": Formatted base price or None if unavailable.
                - "sale_price": Formatted sale price if the product is on sale, otherwise None.
                - "discount_percentage": Discount percentage if applicable, otherwise None.
        """
        inventory = getattr(self, "inventory", None)

        if not inventory:
            return {
                "current_price": None,
                "base_price": None,
                "sale_price": None,
                "discount_percentage": None,
            }

        data = {
            "current_price": inventory.format_current_price(),
            "base_price": inventory.format_base_price(),
            "sale_price": None,
            "discount_percentage": None,
        }

        if inventory.is_on_sale:
            data["sale_price"] = inventory.format_sale_price()
            data["discount_percentage"] = inventory.discount_percentage

        return data

    def is_available_for_purchase(self) -> bool:
        """
        Determine whether the product is currently available for purchase.

        Returns:
            bool: True if the product has an active inventory item that is in stock, False otherwise.
        """
        inventory = self.get_inventory()
        return bool(inventory and inventory.is_active and inventory.is_in_stock)

    def is_in_favorites(self, user: SupportsUserAuth) -> bool:
        """
        Check whether the current product is in the specified user's favorites.

        Args:
            user (User): The user to check favorites for.

        Returns:
            bool: True if the product is in the user's favorites, False otherwise.
        """
        if not user or not user.is_authenticated:
            return False

        if hasattr(self, 'favorites_list'):
            return any(fav.collection.user_id == user.id for fav in self.favorites_list)

        return FavoriteItem.objects.filter(
            collection__user__id=user.id,
            product=self
        ).exists()

    def get_favorites_count(self) -> int:
        """
        Return the number of times this product has been added to users' favorites.

        Returns:
            int: Total count of favorite entries associated with this product.
        """
        if hasattr(self, 'favorites_list'):
            return len(self.favorites_list)

        return FavoriteItem.objects.filter(product=self).count()

    def get_in_carts_users_count(self) -> int:
        """
        Return the number of unique users who have added this product to their carts.

        Returns:
            int: Count of distinct users that have this product in their carts.
        """
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

    def is_in_cart(self, cart: Cart) -> bool:
        """
        Check whether the current product is present in the specified cart.

        Args:
            cart (Cart): The cart instance to check.

        Returns:
            bool: True if the product is in the cart, False otherwise.
        """
        if not cart:
            return False

        if hasattr(self, 'cart_items_list'):
            return any(item.cart_id == cart.id for item in self.cart_items_list)

        return CartItem.objects.filter(product=self, cart=cart).exists()
