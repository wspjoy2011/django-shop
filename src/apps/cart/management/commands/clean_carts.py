import time

from django.core.management.base import BaseCommand

from fixtures.generators.cart import CartsGenerator
from fixtures.db_tuning import (
    optimize_postgresql_for_bulk_operations,
    restore_postgresql_after_bulk_operations,
)
from apps.cart.models import Cart, CartItem


class Command(BaseCommand):
    help = "Clear carts data (deletes CartItems and Carts except for the specified username)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            dest="yes",
            help="Do not prompt for confirmation.",
        )
        parser.add_argument(
            "--exclude-username",
            dest="exclude_username",
            type=str,
            default="admin",
            help="Username to exclude from deletion (default: admin).",
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
        exclude_username = options["exclude_username"]
        skip_optimization = options["skip_optimization"]

        delete_message = f"This will DELETE all carts data - carts and items (except for '{exclude_username}')."

        if not confirmed:
            answer = input(f"{delete_message} Are you sure? Type 'yes' to continue: ")
            if answer.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        stored_indexes = {}
        table_names = [Cart._meta.db_table, CartItem._meta.db_table]
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
            CartsGenerator.clear_all(exclude_username=exclude_username)
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
        self.stdout.write(self.style.SUCCESS(f"Carts data cleared successfully in {total_time:.3f}s"))
