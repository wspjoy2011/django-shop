import time

from django.core.management.base import BaseCommand
from django.db import transaction, DatabaseError

from apps.inventories.models import Currency


class Command(BaseCommand):
    help = 'Clear all currencies data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without interactive prompt',
        )

    def handle(self, *args, **options):
        confirm = options['confirm']

        total_count = Currency.objects.count()

        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No currencies found to delete.')
            )
            return

        if not confirm:
            self.stdout.write(
                self.style.WARNING(f'This will delete {total_count:,} currency records.')
            )

            confirm_input = input('Are you sure? [y/N]: ')
            if confirm_input.lower() not in ['y', 'yes']:
                self.stdout.write('Operation cancelled.')
                return

        start_time = time.time()
        deleted_count = 0

        try:
            with transaction.atomic():
                deleted_count, _ = Currency.objects.all().delete()
        except DatabaseError as e:
            self.stdout.write(
                self.style.ERROR(f'Error deleting currencies: {str(e)}')
            )
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time

            final_count = Currency.objects.count()

            if final_count == 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully deleted {deleted_count:,} currencies')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Deleted {deleted_count:,}, {final_count} remain')
                )

            self.stdout.write(f'Duration: {duration:.2f} seconds')
