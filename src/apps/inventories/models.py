from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


class Currency(models.Model):
    code = models.CharField(
        max_length=3,
        primary_key=True,
        help_text="ISO 4217 currency code (e.g., USD, EUR, JPY)"
    )
    numeric_code = models.SmallIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="ISO 4217 numeric code"
    )
    name = models.CharField(
        max_length=100,
        help_text="Full currency name (e.g., US Dollar)"
    )
    symbol = models.CharField(
        max_length=10,
        blank=True,
        help_text="Currency symbol (e.g., $, €, ¥)"
    )
    decimals = models.SmallIntegerField(
        default=2,
        validators=[MinValueValidator(0)],
        help_text="Number of decimal places for this currency"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this currency is currently active"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ['code']
        indexes = [
            models.Index(fields=['is_active'], name='idx_currency_active'),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def format_amount(self, amount):
        """Format amount with proper decimal places and symbol"""
        if self.decimals == 0:
            formatted = f"{amount:.0f}"
        else:
            formatted = f"{amount:.{self.decimals}f}"

        if self.symbol:
            return f"{self.symbol}{formatted}"
        return f"{formatted} {self.code}"


class ProductInventory(models.Model):
    product = models.OneToOneField(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='inventory',
        help_text="Product this inventory record belongs to"
    )

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base price of the product"
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Sale price (if on sale)"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.RESTRICT,
        default='USD',
        help_text="Currency for pricing"
    )

    stock_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Total stock quantity"
    )
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Reserved/allocated quantity"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this product is active for sale"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Inventory"
        verbose_name_plural = "Product Inventories"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['is_active'], name='idx_inventory_active'),
            models.Index(fields=['stock_quantity'], name='idx_inventory_stock'),
            models.Index(fields=['-updated_at'], name='idx_inventory_updated'),
            models.Index(
                fields=['is_active', 'stock_quantity', 'reserved_quantity'],
                name='idx_inventory_availability'
            ),
            models.Index(
                fields=['sale_price'],
                name='idx_inventory_sale_price'
            ),
            models.Index(
                fields=['is_active', 'sale_price'],
                name='idx_inventory_discount_filter'
            ),
            models.Index(
                fields=['is_active', 'stock_quantity', 'reserved_quantity', 'sale_price'],
                name='idx_inventory_complete_filter'
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(base_price__gte=0),
                name='inventory_base_price_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(sale_price__isnull=True) | models.Q(sale_price__gte=0),
                name='inventory_sale_price_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(reserved_quantity__lte=models.F('stock_quantity')),
                name='inventory_reserved_lte_stock'
            ),
        ]

    def __str__(self):
        return f"Inventory for {self.product.product_display_name}"

    @property
    def available_quantity(self):
        """Calculate available quantity (stock - reserved)"""
        return self.stock_quantity - self.reserved_quantity

    @property
    def is_in_stock(self):
        """Check if product is in stock"""
        return self.available_quantity > 0

    @property
    def current_price(self):
        """Get current effective price (sale price if available, otherwise base price)"""
        return self.sale_price if self.sale_price is not None else self.base_price

    @property
    def is_on_sale(self):
        """Check if product is currently on sale"""
        return self.sale_price is not None and self.sale_price < self.base_price

    @property
    def discount_percentage(self):
        """Calculate discount percentage if on sale"""
        if not self.is_on_sale:
            return 0
        return round(((self.base_price - self.sale_price) / self.base_price) * 100, 2)

    def format_base_price(self):
        """Format base price with currency"""
        return self.currency.format_amount(self.base_price)

    def format_sale_price(self):
        """Format sale price with currency"""
        if self.sale_price is not None:
            return self.currency.format_amount(self.sale_price)
        return None

    def format_current_price(self):
        """Format current effective price with currency"""
        return self.currency.format_amount(self.current_price)

    def reserve_stock(self, quantity):
        """Reserve stock quantity"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if self.reserved_quantity + quantity > self.stock_quantity:
            raise ValueError("Not enough stock to reserve")

        self.reserved_quantity += quantity
        self.save(update_fields=['reserved_quantity', 'updated_at'])

    def release_stock(self, quantity):
        """Release reserved stock"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if quantity > self.reserved_quantity:
            raise ValueError("Cannot release more than reserved")

        self.reserved_quantity -= quantity
        self.save(update_fields=['reserved_quantity', 'updated_at'])

    def add_stock(self, quantity):
        """Add stock quantity"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        self.stock_quantity += quantity
        self.save(update_fields=['stock_quantity', 'updated_at'])

    def remove_stock(self, quantity):
        """Remove stock quantity"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if quantity > self.available_quantity:
            raise ValueError("Not enough available stock")

        self.stock_quantity -= quantity
        self.save(update_fields=['stock_quantity', 'updated_at'])

    def clean(self):
        """Model validation"""

        if self.reserved_quantity > self.stock_quantity:
            raise ValidationError({
                'reserved_quantity': 'Reserved quantity cannot exceed stock quantity'
            })

        if self.sale_price is not None and self.sale_price > self.base_price:
            raise ValidationError({
                'sale_price': 'Sale price cannot be higher than base price'
            })
