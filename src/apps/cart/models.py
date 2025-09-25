from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.utils import timezone

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

    @property
    def is_anonymous(self) -> bool:
        return self.user_id is None and self.token_id is not None

    @property
    def items_count(self) -> int:
        return self.items.count()

    @property
    def total_quantity(self) -> int:
        return sum(i.quantity for i in self.items.all())

    def add_product(self, product, quantity: int = 1):
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")

        item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            defaults={'quantity': quantity},
        )
        if not created:
            CartItem.objects.filter(pk=item.pk).update(quantity=F('quantity') + quantity, updated_at=timezone.now())
            item.refresh_from_db(fields=['quantity', 'updated_at'])
        else:
            item.save()

        self.save(update_fields=['updated_at'])
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

        for item in other.items.all():
            self.add_product(
                product=item.product,
                quantity=item.quantity,
            )
        other.clear()
        return self


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
        ordering = ['-updated_at', '-created_at']

    def __str__(self) -> str:
        return f"{self.cart_id} | {self.product_id} x {self.quantity}"
