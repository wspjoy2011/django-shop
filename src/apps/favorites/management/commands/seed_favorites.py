import time

from django.core.management.base import BaseCommand
from django.db import DatabaseError, transaction

from fixtures.generators.favorites import FavoriteCollectionsGenerator, FavoriteItemsGenerator


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

    def handle(self, *args, **options):
        percentage = options["percentage"]
        min_items = options["min_items"]
        max_items = options["max_items"]
        batch_size = options["batch_size"]
        user_batch_size = options["user_batch_size"]

        if min_items > max_items:
            self.stdout.write(
                self.style.ERROR("min-items cannot be greater than max-items")
            )
            return

        if not (0 < percentage <= 100):
            self.stdout.write(
                self.style.ERROR("percentage must be between 0 and 100")
            )
            return

        total_start = time.perf_counter()

        try:
            with transaction.atomic():
                self.stdout.write(
                    self.style.NOTICE(
                        f"Creating favorite collections for {percentage}% of users..."
                    )
                )
                collections_start = time.perf_counter()

                collections_generator = FavoriteCollectionsGenerator(
                    batch_size=batch_size,
                    use_transaction_per_batch=False
                )
                user_ids = collections_generator.select_users_and_create_collections(percentage)

                collections_time = time.perf_counter() - collections_start
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Collections created in {collections_time:.3f}s for {len(user_ids)} users"
                    )
                )

                if not user_ids:
                    self.stdout.write(self.style.WARNING("No users selected for favorites generation"))
                    return

                self.stdout.write(
                    self.style.NOTICE(
                        f"Generating {min_items}-{max_items} favorite items per collection..."
                    )
                )
                items_start = time.perf_counter()

                items_generator = FavoriteItemsGenerator(
                    batch_size=batch_size,
                    use_transaction_per_batch=False
                )
                items_generator.generate_for_users(user_ids, min_items, max_items, user_batch_size)

                items_time = time.perf_counter() - items_start
                self.stdout.write(
                    self.style.SUCCESS(f"Favorite items generated in {items_time:.3f}s")
                )

                total_time = time.perf_counter() - total_start
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Favorites seeding completed successfully. Total time: {total_time:.3f}s"
                    )
                )

        except DatabaseError as e:
            self.stdout.write(
                self.style.ERROR(f"Error during favorites seeding: {str(e)}")
            )
            self.stdout.write(
                self.style.WARNING("All changes have been rolled back due to the error.")
            )
            raise
