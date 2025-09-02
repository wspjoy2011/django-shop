import time

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.utils import DatabaseError
from apps.catalog.models import Product
from fixtures.generators.ratings import RatingsGenerator
from fixtures.db_tuning import (
    optimize_postgresql_for_bulk_operations,
    restore_postgresql_after_bulk_operations,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Seed ratings, likes and dislikes using fast bulk_create approach."

    def add_arguments(self, parser):
        parser.add_argument(
            "--coverage",
            type=float,
            default=80.0,
            help="Percentage of products to cover with ratings (default: 80.0)",
        )
        parser.add_argument(
            "--ratings-min",
            dest="ratings_min",
            type=int,
            default=50,
            help="Minimum ratings per product (default: 50)",
        )
        parser.add_argument(
            "--ratings-max",
            dest="ratings_max",
            type=int,
            default=500,
            help="Maximum ratings per product (default: 500)",
        )
        parser.add_argument(
            "--likes-min",
            dest="likes_min",
            type=int,
            default=20,
            help="Minimum likes per product (default: 20)",
        )
        parser.add_argument(
            "--likes-max",
            dest="likes_max",
            type=int,
            default=200,
            help="Maximum likes per product (default: 200)",
        )
        parser.add_argument(
            "--dislikes-min",
            dest="dislikes_min",
            type=int,
            default=5,
            help="Minimum dislikes per product (default: 5)",
        )
        parser.add_argument(
            "--dislikes-max",
            dest="dislikes_max",
            type=int,
            default=50,
            help="Maximum dislikes per product (default: 50)",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=50000,
            help="Batch size for bulk operations (default: 50000)",
        )
        parser.add_argument(
            "--no-batch-tx",
            action="store_true",
            dest="no_batch_tx",
            default=False,
            help="Disable per-batch transactions for maximum speed.",
        )
        parser.add_argument(
            "--skip-optimization",
            action="store_true",
            dest="skip_optimization",
            default=False,
            help="Do not drop indexes or apply PostgreSQL optimizations.",
        )

    def handle(self, *args, **options):
        coverage = options["coverage"]
        ratings_min = options["ratings_min"]
        ratings_max = options["ratings_max"]
        likes_min = options["likes_min"]
        likes_max = options["likes_max"]
        dislikes_min = options["dislikes_min"]
        dislikes_max = options["dislikes_max"]
        batch_size = options["batch_size"]
        use_transaction_per_batch = not options["no_batch_tx"]
        skip_optimization = options["skip_optimization"]

        if not (0 < coverage <= 100):
            raise CommandError("Coverage must be between 0 and 100")
        if ratings_min > ratings_max:
            raise CommandError("ratings-min cannot be greater than ratings-max")
        if likes_min > likes_max:
            raise CommandError("likes-min cannot be greater than likes-max")
        if dislikes_min > dislikes_max:
            raise CommandError("dislikes-min cannot be greater than dislikes-max")

        users_count = User.objects.count()
        products_count = Product.objects.count()

        if users_count == 0:
            raise CommandError("No users found. Please create users first with: python manage.py seed_users")
        if products_count == 0:
            raise CommandError("No products found. Please seed catalog first with: python manage.py seed_catalog")

        self.stdout.write(
            self.style.NOTICE(
                f"Starting ratings generation with following parameters:\n"
                f"  Coverage: {coverage}% of {products_count:,} products\n"
                f"  Ratings: {ratings_min}-{ratings_max} per product\n"
                f"  Likes: {likes_min}-{likes_max} per product\n"
                f"  Dislikes: {dislikes_min}-{dislikes_max} per product\n"
                f"  Batch size: {batch_size:,}\n"
                f"  Per-batch transactions: {use_transaction_per_batch}\n"
                f"  PostgreSQL optimization: {not skip_optimization}\n"
                f"  Available users: {users_count:,}"
            )
        )

        stored_indexes = {}
        if not skip_optimization:
            self.stdout.write(self.style.NOTICE("Optimizing PostgreSQL for bulk operations..."))
            t0 = time.perf_counter()
            table_names = ['ratings_rating', 'ratings_like', 'ratings_dislike']
            stored_indexes, drop_results = optimize_postgresql_for_bulk_operations(table_names)

            ok = sum(1 for v in drop_results.values() if v)
            fail = sum(1 for v in drop_results.values() if not v)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Optimization complete: {ok} indexes dropped, {fail} failed in {time.perf_counter() - t0:.3f}s"
                )
            )
            if fail:
                failed_list = ", ".join([k for k, v in drop_results.items() if not v])
                self.stdout.write(self.style.WARNING(f"Failed to drop: {failed_list}"))

        start_time = time.perf_counter()

        generation_error: DatabaseError | None = None
        generator = RatingsGenerator(batch_size=batch_size, use_transaction_per_batch=use_transaction_per_batch)

        try:
            generator.generate_all_ratings(
                products_coverage_percent=coverage,
                ratings_per_product_range=(ratings_min, ratings_max),
                likes_per_product_range=(likes_min, likes_max),
                dislikes_per_product_range=(dislikes_min, dislikes_max)
            )
        except DatabaseError as exc:
            generation_error = exc
        finally:
            if not skip_optimization and stored_indexes:
                self.stdout.write(self.style.NOTICE("Restoring PostgreSQL after bulk operations..."))
                t1 = time.perf_counter()
                recreate_results = restore_postgresql_after_bulk_operations(stored_indexes)
                ok = sum(1 for v in recreate_results.values() if v)
                fail = sum(1 for v in recreate_results.values() if not v)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Restoration complete: {ok} indexes recreated, {fail} failed in {time.perf_counter() - t1:.3f}s"
                    )
                )
                if fail:
                    failed_list = ", ".join([k for k, v in recreate_results.items() if not v])
                    self.stdout.write(self.style.WARNING(f"Failed to recreate: {failed_list}"))

        if generation_error:
            raise generation_error

        total_time = time.perf_counter() - start_time

        stats = generator.get_statistics()

        self.stdout.write(
            self.style.SUCCESS(
                f"Ratings generation completed successfully. Total time: {total_time:.3f}s"
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                f"Generation Statistics:\n"
                f"  Total ratings: {stats['total_ratings']:,}\n"
                f"  Total likes: {stats['total_likes']:,}\n"
                f"  Total dislikes: {stats['total_dislikes']:,}\n"
                f"  Products with ratings: {stats['products_with_ratings']:,}\n"
                f"  Products with likes: {stats['products_with_likes']:,}\n"
                f"  Products with dislikes: {stats['products_with_dislikes']:,}"
            )
        )

        total_records = stats['total_ratings'] + stats['total_likes'] + stats['total_dislikes']
        records_per_second = total_records / total_time if total_time > 0 else 0
        self.stdout.write(self.style.NOTICE(f"Performance: {records_per_second:.1f} records/second"))
