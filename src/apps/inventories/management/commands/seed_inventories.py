import time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import DatabaseError

from fixtures.generators.inventories import ProductInventoryGenerator
from apps.inventories.models import ProductInventory, Currency
from apps.catalog.models import Product


class Command(BaseCommand):
    help = 'Generate product inventory data for all products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for bulk operations (default: 1000)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing inventory before generating',
        )
        parser.add_argument(
            '--transaction-per-batch',
            action='store_true',
            help='Use transaction per batch (default: single transaction)',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        clear_existing = options['clear']
        use_transaction_per_batch = options['transaction_per_batch']

        if not Currency.objects.filter(code='USD').exists():
            self.stdout.write(
                self.style.ERROR('USD currency not found. Please run: python manage.py generate_currencies')
            )
            return

        products_count = Product.objects.count()
        if products_count == 0:
            self.stdout.write(
                self.style.ERROR('No products found. Please generate products first.')
            )
            return

        if clear_existing:
            with transaction.atomic():
                deleted_count, _ = ProductInventory.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(f'Cleared {deleted_count} existing inventory records')
                )

        existing_count = ProductInventory.objects.count()
        if existing_count > 0 and not clear_existing:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {existing_count} existing inventory records. Use --clear to replace them.'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Starting inventory generation for {products_count} products...')
        )
        self.stdout.write(f'Configuration:')
        self.stdout.write(f'  * Batch size: {batch_size}')
        self.stdout.write(f'  * Transaction per batch: {use_transaction_per_batch}')
        self.stdout.write(f'  * ~20% products will be out of stock')
        self.stdout.write(f'  * ~15% products will have sales (5-20% discount)')
        self.stdout.write(f'  * Price range: $5.00 - $1000.00')

        start_time = time.time()

        generator = ProductInventoryGenerator(
            batch_size=batch_size,
            use_transaction_per_batch=use_transaction_per_batch,
        )

        try:
            generator.generate()
        except DatabaseError as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating inventory: {str(e)}')
            )
        finally:
            end_time = time.time()
            duration = end_time - start_time

            final_count = ProductInventory.objects.count()
            on_sale_count = ProductInventory.objects.filter(sale_price__isnull=False).count()
            out_of_stock_count = ProductInventory.objects.filter(stock_quantity=0).count()

            self.stdout.write(
                self.style.SUCCESS(f'Successfully generated inventory!')
            )
            self.stdout.write(f'Statistics:')
            self.stdout.write(f'  * Total inventory records: {final_count:,}')
            self.stdout.write(f'  * Products on sale: {on_sale_count:,} ({on_sale_count / final_count * 100:.1f}%)')
            self.stdout.write(
                f'  * Out of stock products: {out_of_stock_count:,} ({out_of_stock_count / final_count * 100:.1f}%)')
            self.stdout.write(f'  * Generation time: {duration:.2f} seconds')
            self.stdout.write(f'  * Rate: {final_count / duration:.0f} records/second')
