import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from fixtures.cleaners.users import UserCleaner
from fixtures.db_tuning import (
    optimize_postgresql_for_bulk_operations,
    restore_postgresql_after_bulk_operations,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Clear user data (deletes all users except superusers)."

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
        current_users = User.objects.count()
        admin_users = User.objects.filter(is_superuser=True).count()
        users_to_delete = current_users - admin_users

        self.stdout.write(
            self.style.NOTICE(
                f"Current users: {current_users:,} total, {admin_users} superuser(s), "
                f"{users_to_delete:,} will be deleted"
            )
        )

        if users_to_delete == 0:
            self.stdout.write(self.style.WARNING("No regular users to delete."))
            return

        confirmed = options["yes"]
        if not confirmed:
            answer = input(
                f"This will DELETE {users_to_delete:,} users (keeping superusers). "
                "Are you sure? Type 'yes' to continue: "
            )
            if answer.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        skip_optimization = options["skip_optimization"]
        stored_indexes = {}
        if not skip_optimization:
            self.stdout.write(self.style.NOTICE("Optimizing PostgreSQL for bulk deletion..."))
            t0 = time.perf_counter()
            table_names = [User._meta.db_table]
            stored_indexes, drop_results = optimize_postgresql_for_bulk_operations(table_names)
            ok = sum(1 for v in drop_results.values() if v)
            fail = sum(1 for v in drop_results.values() if not v)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Optimization complete: {ok} indexes dropped, {fail} failed in {time.perf_counter() - t0:.3f}s"
                )
            )

        self.stdout.write(self.style.NOTICE("Clearing user data..."))
        start = time.perf_counter()

        try:
            cleaner = UserCleaner()
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

        total_time = time.perf_counter() - start

        remaining_users = User.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Users cleared in {total_time:.3f}s. "
                f"Remaining users: {remaining_users:,}"
            )
        )
