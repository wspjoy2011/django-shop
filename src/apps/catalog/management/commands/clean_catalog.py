import time

from django.core.management.base import BaseCommand
from etl.cleaner import DjangoCatalogCleaner
from fixtures.db_tuning import (
    optimize_postgresql_for_bulk_operations,
    restore_postgresql_after_bulk_operations,
)
from apps.catalog.models import (
    Product,
    ArticleType,
    SubCategory,
    MasterCategory,
    BaseColour,
    Season,
    UsageType
)


class Command(BaseCommand):
    help = "Clear catalog data (deletes Products, ArticleTypes, SubCategories, MasterCategories, BaseColours, Seasons, UsageTypes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            dest="yes",
            help="Do not prompt for confirmation.",
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
        if not confirmed:
            answer = input(
                "This will DELETE all catalog data. Are you sure? Type 'yes' to continue: "
            )
            if answer.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        skip_optimization = options["skip_optimization"]
        stored_indexes = {}
        table_names = [
            Product._meta.db_table,
            ArticleType._meta.db_table,
            SubCategory._meta.db_table,
            MasterCategory._meta.db_table,
            BaseColour._meta.db_table,
            Season._meta.db_table,
            UsageType._meta.db_table,
        ]

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

        self.stdout.write(self.style.NOTICE("Clearing catalog tables..."))
        start = time.perf_counter()

        try:
            cleaner = DjangoCatalogCleaner()
            cleaner.clean()
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

        total = time.perf_counter() - start
        self.stdout.write(self.style.SUCCESS(f"Catalog cleared in {total:.3f}s"))
