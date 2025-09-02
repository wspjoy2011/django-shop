import random
from decimal import Decimal
from contextlib import nullcontext
from typing import List

from django.db import transaction
from tqdm import tqdm

from apps.inventories.models import Currency, ProductInventory
from apps.catalog.models import Product


class CurrenciesGenerator:

    def __init__(self, batch_size: int = 1000, use_transaction_per_batch: bool = False):
        self.batch_size = batch_size
        self.use_transaction_per_batch = use_transaction_per_batch

    def generate(self) -> None:
        currencies_data = [
            {
                'code': 'USD',
                'numeric_code': 840,
                'name': 'US Dollar',
                'symbol': '$',
                'decimals': 2,
                'is_active': True,
            },
            {
                'code': 'EUR',
                'numeric_code': 978,
                'name': 'Euro',
                'symbol': '€',
                'decimals': 2,
                'is_active': True,
            },
        ]

        currencies_batch = []
        for currency_data in currencies_data:
            currencies_batch.append(Currency(**currency_data))

        self._bulk_create_currencies(currencies_batch)

    def _bulk_create_currencies(self, currencies_batch: List[Currency]) -> None:
        transaction_context = transaction.atomic() if self.use_transaction_per_batch else nullcontext()
        with transaction_context:
            Currency.objects.bulk_create(
                currencies_batch,
                batch_size=self.batch_size,
                ignore_conflicts=True
            )


class ProductInventoryGenerator:
    """Generate product inventory data efficiently"""

    def __init__(self, batch_size: int = 1000, use_transaction_per_batch: bool = False):
        self.batch_size = batch_size
        self.use_transaction_per_batch = use_transaction_per_batch

        self.stock_distribution = {
            0: 10,  # out of stock (0)
            1: 30,  # 1–10
            2: 20,  # 11–20
            3: 15,  # 21–40
            4: 15,  # 41–60
            5: 7,  # 61–80
            6: 3,  # 81–100
        }

        self.price_ranges = {
            'default': (5, 50),
            'footwear': (25, 200),
            'apparel': (10, 150),
            'watches': (50, 500),
            'accessories': (5, 100),
        }

    def generate(self) -> None:
        """Generate inventory for all products"""
        products = list(Product.objects.select_related(
            'article_type',
            'article_type__sub_category',
            'article_type__sub_category__master_category'
        ).values_list('pk', flat=True))

        if not products:
            print("No products found to generate inventory for")
            return

        try:
            usd_currency = Currency.objects.get(code='USD')
        except Currency.DoesNotExist:
            print("USD currency not found. Please generate currencies first.")
            return

        total_products = len(products)
        print(f"Generating inventory for {total_products} products...")

        inventory_batch = []
        batch_count = 0

        progress_bar = tqdm(products, desc="Generating inventory", unit="products")

        for product_id in progress_bar:
            inventory = self._create_inventory_for_product(product_id, usd_currency)
            inventory_batch.append(inventory)

            if len(inventory_batch) >= self.batch_size:
                self._bulk_create_inventory(inventory_batch)
                batch_count += 1
                progress_bar.set_postfix(batches=batch_count)
                inventory_batch = []

        if inventory_batch:
            self._bulk_create_inventory(inventory_batch)
            batch_count += 1

        print(f"Generated inventory for {total_products} products in {batch_count} batches")

    def _create_inventory_for_product(self, product_id: int, currency: Currency) -> ProductInventory:
        """Create inventory record for a single product"""

        base_price = Decimal(str(round(random.uniform(5.0, 1000.0), 2)))

        sale_price = None
        if random.random() < 0.15:
            discount_percent = random.uniform(0.05, 0.20)
            sale_price = Decimal(str(round(float(base_price) * (1 - discount_percent), 2)))

        stock_quantity = self._generate_stock_quantity()

        if stock_quantity > 0:
            max_reserved = min(stock_quantity, max(1, int(stock_quantity * 0.2)))
            reserved_quantity = random.randint(0, max_reserved)
        else:
            reserved_quantity = 0

        is_active = stock_quantity > 0 or random.random() < 0.95

        return ProductInventory(
            product_id=product_id,
            base_price=base_price,
            sale_price=sale_price,
            currency=currency,
            stock_quantity=stock_quantity,
            reserved_quantity=reserved_quantity,
            is_active=is_active,
        )

    def _generate_stock_quantity(self) -> int:
        """Generate stock quantity based on distribution weights"""
        categories = list(self.stock_distribution.keys())
        weights = list(self.stock_distribution.values())

        bucket = random.choices(categories, weights=weights, k=1)[0]

        ranges = {
            0: (0, 0),
            1: (1, 10),
            2: (11, 20),
            3: (21, 40),
            4: (41, 60),
            5: (61, 80),
            6: (81, 100),
        }

        low, high = ranges[bucket]
        if low == high:
            return low
        return random.randint(low, high)

    def _bulk_create_inventory(self, inventory_batch: List[ProductInventory]) -> None:
        """Bulk create inventory records"""
        transaction_context = transaction.atomic() if self.use_transaction_per_batch else nullcontext()
        with transaction_context:
            ProductInventory.objects.bulk_create(
                inventory_batch,
                batch_size=self.batch_size,
                ignore_conflicts=True
            )
