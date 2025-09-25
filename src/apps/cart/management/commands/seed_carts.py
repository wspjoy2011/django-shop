import time

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from fixtures.generators.cart import CartsGenerator
from fixtures.db_tuning import (
    optimize_postgresql_for_bulk_operations,
    restore_postgresql_after_bulk_operations,
)
from apps.cart.models import Cart, CartItem


class Command(BaseCommand):
    help = "Seed carts and cart items for a fraction of users (excluding a specific username)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--percentage",
            dest="percentage",
            type=float,
            default=30.0,
            help="Percentage of users to create carts for (default: 30.0)",
        )
        parser.add_argument(
            "--min-items",
            dest="min_items",
            type=int,
            default=1,
            help="Minimum number of distinct items per cart (default: 1)",
        )
        parser.add_argument(
            "--max-items",
            dest="max_items",
            type=int,
            default=10,
            help="Maximum number of distinct items per cart (default: 10)",
        )
        parser.add_argument(
            "--min-qty",
            dest="min_qty",
            type=int,
            default=1,
            help="Minimum quantity per item (default: 1)",
        )
        parser.add_argument(
            "--max-qty",
            dest="max_qty",
            type=int,
            default=5,
            help="Maximum quantity per item (default: 5)",
        )
        parser.add_argument(
            "--exclude-username",
            dest="exclude_username",
            type=str,
            default="admin",
            help="Username to exclude from seeding (default: admin)",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=50000,
            help="Batch size for cursor fetch (default: 50000)",
        )
        parser.add_argument(
            "--skip-optimization",
            action="store_true",
            dest="skip_optimization",
            default=False,
            help="Do not drop indexes or apply PostgreSQL optimizations.",
        )

    def handle(self, *args, **options):
        percentage = options["percentage"]
        min_items = options["min_items"]
        max_items = options["max_items"]
        min_qty = options["min_qty"]
        max_qty = options["max_qty"]
        exclude_username = options["exclude_username"]
        batch_size = options["batch_size"]
        skip_optimization = options["skip_optimization"]

        if not (0 < percentage <= 100):
            raise CommandError("percentage must be between 0 and 100")
        if min_items > max_items:
            raise CommandError("min-items cannot be greater than max-items")
        if min_qty > max_qty:
            raise CommandError("min-qty cannot be greater than max-qty")

        stored_indexes = {}
        table_names = [Cart._meta.db_table, CartItem._meta.db_table]
        if not skip_optimization:
            self.stdout.write(self.style.NOTICE("Optimizing PostgreSQL for bulk insert..."))
            t0 = time.perf_counter()
            stored_indexes, drop_results = optimize_postgresql_for_bulk_operations(table_names)
            ok = sum(1 for v in drop_results.values() if v)
            fail = sum(1 for v in drop_results.values() if not v)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Optimization complete: {ok} indexes dropped, {fail} failed in {time.perf_counter() - t0:.3f}s"
                )
            )

        total_start = time.perf_counter()
        seeding_error = None

        try:
            with transaction.atomic():
                self.stdout.write(
                    self.style.NOTICE(
                        f"Creating carts for {percentage}% of users (excluding '{exclude_username}')..."
                    )
                )

                generator = CartsGenerator(
                    user_fraction=percentage / 100.0,
                    items_range=(min_items, max_items),
                    quantity_range=(min_qty, max_qty),
                    exclude_username=exclude_username,
                    batch_size=batch_size,
                )
                generator.generate()
        except DatabaseError as e:
            seeding_error = e
        finally:
            if not skip_optimization and stored_indexes:
                self.stdout.write(self.style.NOTICE("Restoring PostgreSQL after bulk insert..."))
                t1 = time.perf_counter()
                recreate_results = restore_postgresql_after_bulk_operations(stored_indexes)
                ok = sum(1 for v in recreate_results.values() if v)
                fail = sum(1 for v in recreate_results.values() if not v)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Restoration complete: {ok} indexes recreated, {fail} failed in {time.perf_counter() - t1:.3f}s"
                    )
                )

        if seeding_error:
            self.stdout.write(self.style.ERROR(f"Error during carts seeding: {str(seeding_error)}"))
            self.stdout.write(self.style.WARNING("All changes have been rolled back due to transaction.atomic()."))
            raise seeding_error

        total_time = time.perf_counter() - total_start
        self.stdout.write(self.style.SUCCESS(f"Carts seeding completed successfully in {total_time:.3f}s"))
