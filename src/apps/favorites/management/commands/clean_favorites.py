import time

from django.core.management.base import BaseCommand, CommandError
from fixtures.generators.favorites import FavoriteCollectionsGenerator, FavoriteItemsGenerator
from fixtures.db_tuning import (
    optimize_postgresql_for_bulk_operations,
    restore_postgresql_after_bulk_operations,
)
from apps.favorites.models import FavoriteCollection, FavoriteItem


class Command(BaseCommand):
    help = "Clear favorites data (deletes FavoriteItems and FavoriteCollections except for admin user)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            dest="yes",
            help="Do not prompt for confirmation.",
        )
        parser.add_argument(
            "--items-only",
            action="store_true",
            dest="items_only",
            help="Delete only favorite items, keep collections.",
        )
        parser.add_argument(
            "--collections-only",
            action="store_true",
            dest="collections_only",
            help="Delete only collections (and their items).",
        )
        parser.add_argument(
            "--skip-optimization",
            action="store_true",
            dest="skip_optimization",
            default=False,
            help="Do not drop indexes or apply PostgreSQL optimizations.",
        )

    def handle(self, *args, **options):
        confirmed = options["yes"]
        items_only = options["items_only"]
        collections_only = options["collections_only"]
        skip_optimization = options["skip_optimization"]

        if items_only and collections_only:
            raise CommandError("Cannot use both --items-only and --collections-only")

        if items_only:
            delete_message = "This will DELETE all favorite items (except for admin user)."
        elif collections_only:
            delete_message = "This will DELETE all favorite collections and their items (except for admin user)."
        else:
            delete_message = "This will DELETE all favorites data - collections and items (except for admin user)."

        if not confirmed:
            answer = input(f"{delete_message} Are you sure? Type 'yes' to continue: ")
            if answer.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        stored_indexes = {}
        table_names = [FavoriteCollection._meta.db_table, FavoriteItem._meta.db_table]
        if not skip_optimization:
            self.stdout.write(self.style.NOTICE("Optimizing PostgreSQL for bulk deletion..."))
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

        try:
            if not collections_only:
                self.stdout.write(self.style.NOTICE("Clearing favorite items..."))
                items_generator = FavoriteItemsGenerator()
                items_generator.clear_all_items_except_admin()

            if not items_only:
                self.stdout.write(self.style.NOTICE("Clearing favorite collections..."))
                collections_generator = FavoriteCollectionsGenerator()
                collections_generator.clear_all_collections_except_admin()
        finally:
            if not skip_optimization and stored_indexes:
                self.stdout.write(self.style.NOTICE("Restoring PostgreSQL after bulk deletion..."))
                t1 = time.perf_counter()
                recreate_results = restore_postgresql_after_bulk_operations(stored_indexes)
                ok = sum(1 for v in recreate_results.values() if v)
                fail = sum(1 for v in recreate_results.values() if not v)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Restoration complete: {ok} indexes recreated, {fail} failed in {time.perf_counter() - t1:.3f}s"
                    )
                )

        total_time = time.perf_counter() - total_start
        self.stdout.write(
            self.style.SUCCESS(f"Favorites data cleared successfully in {total_time:.3f}s")
        )
