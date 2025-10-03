from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from apps.cart.exceptions import NotEnoughStockError, ProductUnavailableError, CartItemNotFoundError
from apps.cart.query_fields import CART_ITEM_SELECT_RELATED, CART_ITEM_ONLY_FIELDS
from apps.inventories.models import ProductInventory

User = get_user_model()


def default_cart_token_expiry():
    return timezone.now() + settings.CART_TOKEN_LIFETIME


class CartToken(models.Model):
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique token used to identify anonymous carts via cookie."
    )
    expires_at = models.DateTimeField(
        default=default_cart_token_expiry,
        help_text="Token expiration; anonymous carts past this date may be culled."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"CartToken({self.token})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class Cart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        null=True,
        blank=True,
        help_text="Owner for authenticated carts. Mutually exclusive with `token`."
    )
    token = models.OneToOneField(
        CartToken,
        on_delete=models.CASCADE,
        related_name='cart',
        null=True,
        blank=True,
        help_text="Anonymous cart token. Mutually exclusive with `user`."
    )

    products = models.ManyToManyField(
        'catalog.Product',
        through='CartItem',
        related_name='carts',
        blank=True,
        help_text="Products in this cart via CartItem"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']
        constraints = [
            models.CheckConstraint(
                check=(
                        (models.Q(user__isnull=False) & models.Q(token__isnull=True)) |
                        (models.Q(user__isnull=True) & models.Q(token__isnull=False))
                ),
                name='cart_exactly_one_owner'
            ),
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(user__isnull=False),
                name='unique_cart_per_user'
            ),
            models.UniqueConstraint(
                fields=['token'],
                condition=models.Q(token__isnull=False),
                name='unique_cart_per_token'
            ),
        ]

    def __str__(self) -> str:
        owner = self.user_id or (self.token.token if self.token_id else 'unknown')
        return f"Cart<{owner}>"

    def clean(self):
        super().clean()
        if (self.user and self.token) or (not self.user and not self.token):
            raise ValidationError("Exactly one of `user` or `token` must be set.")

    def _get_available_items_list(self):
        items = getattr(self, "available_items_list", None)
        return items

    @property
    def items_available_count(self) -> int:
        return len(self._get_available_items_list())

    @property
    def total_quantity_available(self) -> int:
        return sum(item.quantity for item in self._get_available_items_list())

    def subtotal_amount(self) -> Decimal:
        total = Decimal("0.00")
        for item in self._get_available_items_list():
            inv = item.product.inventory
            total += inv.base_price * item.quantity
        return total

    def discount_amount(self) -> Decimal:
        total = Decimal("0.00")
        for item in self._get_available_items_list():
            inv = item.product.inventory
            if inv.sale_price is not None and inv.sale_price < inv.base_price:
                total += (inv.base_price - inv.sale_price) * item.quantity
        return total

    def total_amount(self) -> Decimal:
        return self.subtotal_amount() - self.discount_amount()

    def subtotal_formatted(self) -> str:
        items = self._get_available_items_list()
        if not items:
            return "0.00"
        currency = items[0].product.inventory.currency
        return currency.format_amount(self.subtotal_amount())

    def discount_formatted(self) -> str:
        items = self._get_available_items_list()
        if not items:
            return "0.00"
        currency = items[0].product.inventory.currency
        return currency.format_amount(self.discount_amount())

    def total_formatted(self) -> str:
        items = self._get_available_items_list()
        if not items:
            return "0.00"
        currency = items[0].product.inventory.currency
        return currency.format_amount(self.total_amount())

    @property
    def is_anonymous(self) -> bool:
        return self.user_id is None and self.token_id is not None

    @property
    def items_count(self) -> int:
        items = getattr(self, "items_list", None)
        if items is not None:
            return len(items)
        return self.items.count()

    @property
    def total_quantity(self) -> int:
        return sum(i.quantity for i in self.items.all())

    @property
    def total_value(self):
        return (
                self.items
                .annotate(
                    effective_price=Coalesce(F("product__inventory__sale_price"),
                                             F("product__inventory__base_price"))
                )
                .aggregate(
                    total=Sum(F("effective_price") * F("quantity"))
                )["total"] or 0
        )

    def has_product(self, product) -> bool:
        return self.items.filter(product=product).exists()

    def add_product(self, product, quantity: int = 1):
        if quantity <= 0:
            raise ValidationError("Step must be positive.")

        with transaction.atomic():
            inventory = (
                ProductInventory.objects
                .select_for_update()
                .only("id", "is_active", "stock_quantity", "reserved_quantity")
                .get(product_id=product.pk)
            )

            if not inventory.is_active or not inventory.is_in_stock:
                raise ProductUnavailableError()

            existing_item = (
                CartItem.objects
                .filter(cart=self, product=product)
                .only("id", "quantity")
                .first()
            )
            current_quantity = existing_item.quantity if existing_item else 0
            new_quantity = current_quantity + quantity

            if new_quantity > inventory.available_quantity:
                raise NotEnoughStockError()

            if existing_item:
                CartItem.objects.filter(pk=existing_item.pk).update(
                    quantity=F("quantity") + quantity,
                    updated_at=timezone.now(),
                )
                existing_item.refresh_from_db(fields=["quantity", "updated_at"])
                self.save(update_fields=["updated_at"])
                return existing_item

            item = CartItem.objects.create(cart=self, product=product, quantity=quantity)
            self.save(update_fields=["updated_at"])
        return item

    def decrease_product(self, product, step: int = 1):
        if step <= 0:
            raise ValidationError("Step must be positive.")

        with transaction.atomic():
            item = (
                CartItem.objects
                .select_for_update()
                .only("id", "quantity")
                .filter(cart=self, product=product)
                .first()
            )
            if not item:
                raise CartItemNotFoundError()

            if item.quantity <= step:
                CartItem.objects.filter(pk=item.pk).delete()
                self.save(update_fields=["updated_at"])
                raise NotEnoughStockError()

            CartItem.objects.filter(pk=item.pk).update(
                quantity=F("quantity") - step,
                updated_at=timezone.now(),
            )
            item.refresh_from_db(fields=["quantity", "updated_at"])
            self.save(update_fields=["updated_at"])
            return item

    def set_item_quantity(self, product, quantity: int):
        try:
            item = self.items.get(product=product)
        except CartItem.DoesNotExist:
            if quantity <= 0:
                return None
            return self.add_product(product, quantity=quantity)

        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save(update_fields=['quantity', 'updated_at'])
        self.save(update_fields=['updated_at'])
        return item

    def remove_product(self, product):
        deleted, _ = self.items.filter(product=product).delete()
        if deleted:
            self.save(update_fields=['updated_at'])
        return deleted

    def clear(self):
        self.items.all().delete()
        self.save(update_fields=['updated_at'])

    @classmethod
    def get_or_create_for_user(cls, user: User):
        cart, _ = cls.objects.get_or_create(user=user)
        return cart

    @classmethod
    def get_or_create_for_token(cls, token: CartToken):
        cart, _ = cls.objects.get_or_create(token=token)
        return cart

    def merge_from(self, other: 'Cart'):
        if other.pk == self.pk:
            return self

        for item in other.items.select_related("product", "product__inventory").all():
            self.add_product(
                product=item.product,
                quantity=item.quantity
            )

        other.clear()
        return self

    @staticmethod
    def users_with_product_count(product) -> int:
        return (
            CartItem.objects
            .filter(product=product)
            .values("cart_id")
            .distinct()
            .count()
        )

    def get_summary(self):
        return {
            "total_quantity": self.total_quantity_available,
            "total_subtotal": self.subtotal_formatted(),
            "total_discount": self.discount_formatted(),
            "total_value": self.total_formatted(),
            "total_items": self.items_count
        }


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        db_index=True
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='cart_items',
        db_index=True
    )

    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('cart', 'product')]
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.cart_id} | {self.product_id} x {self.quantity}"

    @property
    def line_total(self):
        inv = self.product.inventory
        return inv.current_price * self.quantity

    @property
    def format_line_total(self):
        inv = self.product.inventory
        return inv.currency.format_amount(self.line_total)

    def get_api_increase_url(self):
        return reverse("api:cart_item_increase", kwargs={"product_id": self.product_id})

    def get_api_decrease_url(self):
        return reverse("api:cart_item_decrease", kwargs={"product_id": self.product_id})
