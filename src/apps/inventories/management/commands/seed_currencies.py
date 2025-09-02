from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import DatabaseError

from fixtures.generators.inventories import CurrenciesGenerator
from apps.inventories.models import Currency


class Command(BaseCommand):
    help = 'Generate currencies data (USD and EUR)'

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
            help='Clear existing currencies before generating',
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

        if clear_existing:
            with transaction.atomic():
                deleted_count, _ = Currency.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(f'Cleared {deleted_count} existing currencies')
                )

        existing_count = Currency.objects.count()
        if existing_count > 0 and not clear_existing:
            self.stdout.write(
                self.style.WARNING(f'Found {existing_count} existing currencies. Use --clear to replace them.')
            )
            return

        self.stdout.write('Starting currency generation...')

        generator = CurrenciesGenerator(
            batch_size=batch_size,
            use_transaction_per_batch=use_transaction_per_batch,
        )

        try:
            with transaction.atomic():
                generator.generate()
        except DatabaseError as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating currencies: {str(e)}')
            )
        finally:
            final_count = Currency.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully generated currencies. Total: {final_count}')
            )
