import time

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from fixtures.generators.favorites import FavoriteCollectionsGenerator, FavoriteItemsGenerator
from fixtures.db_tuning import (
    optimize_postgresql_for_bulk_operations,
    restore_postgresql_after_bulk_operations,
)
from apps.favorites.models import FavoriteCollection, FavoriteItem


class Command(BaseCommand):
    help = "Seed favorite collections and items for users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--percentage",
            dest="percentage",
            type=float,
            default=30.0,
            help="Percentage of users to create favorite collections for (default: 30.0)",
        )
        parser.add_argument(
            "--min-items",
            dest="min_items",
            type=int,
            default=10,
            help="Minimum number of favorite items per collection (default: 10)",
        )
        parser.add_argument(
            "--max-items",
            dest="max_items",
            type=int,
            default=50,
            help="Maximum number of favorite items per collection (default: 50)",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=10000,
            help="Bulk insert batch size for seeding (default: 10000)",
        )
        parser.add_argument(
            "--user-batch-size",
            dest="user_batch_size",
            type=int,
            default=1000,
            help="User batch size to avoid SQLite variable limit (default: 1000)",
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
        batch_size = options["batch_size"]
        user_batch_size = options["user_batch_size"]
        skip_optimization = options["skip_optimization"]

        if min_items > max_items:
            raise CommandError("min-items cannot be greater than max-items")
        if not (0 < percentage <= 100):
            raise CommandError("percentage must be between 0 and 100")

        stored_indexes = {}
        table_names = [FavoriteCollection._meta.db_table, FavoriteItem._meta.db_table]
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
                    self.style.NOTICE(f"Creating favorite collections for {percentage}% of users...")
                )
                collections_generator = FavoriteCollectionsGenerator(
                    batch_size=batch_size, use_transaction_per_batch=False
                )
                user_ids = collections_generator.select_users_and_create_collections(percentage)

                if not user_ids:
                    self.stdout.write(self.style.WARNING("No users selected for favorites generation, skipping item creation."))
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"Collections created for {len(user_ids)} users.")
                    )
                    self.stdout.write(
                        self.style.NOTICE(f"Generating {min_items}-{max_items} favorite items per collection...")
                    )
                    items_generator = FavoriteItemsGenerator(
                        batch_size=batch_size, use_transaction_per_batch=False
                    )
                    items_generator.generate_for_users(user_ids, min_items, max_items, user_batch_size)

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
            self.stdout.write(self.style.ERROR(f"Error during favorites seeding: {str(seeding_error)}"))
            self.stdout.write(self.style.WARNING("All changes have been rolled back due to the error and transaction.atomic()."))
            raise seeding_error

        total_time = time.perf_counter() - total_start
        self.stdout.write(
            self.style.SUCCESS(f"Favorites seeding completed successfully. Total time: {total_time:.3f}s")
        )
