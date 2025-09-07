import time

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from fixtures.generators.users import UserGenerator
from fixtures.db_tuning import (
    optimize_postgresql_for_bulk_operations,
    restore_postgresql_after_bulk_operations,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Seed users using fast bulk_create approach."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=500000,
            help="Total number of users to generate (default: 500000)",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=5000,
            help="How many users to create at once (default: 5000)",
        )
        parser.add_argument(
            "--password",
            dest="password",
            type=str,
            default="password123",
            help="Password for all generated users (default: password123)",
        )
        parser.add_argument(
            "--email-domain",
            dest="email_domain",
            type=str,
            default="example.com",
            help="Email domain for generated users (default: example.com)",
        )
        parser.add_argument(
            "--skip-optimization",
            action="store_true",
            dest="skip_optimization",
            default=False,
            help="Do not drop indexes or apply PostgreSQL optimizations.",
        )

    def handle(self, *args, **options):
        total_count = options["count"]
        batch_size = options["batch_size"]
        password = options["password"]
        email_domain = options["email_domain"]
        skip_optimization = options["skip_optimization"]

        self.stdout.write(
            self.style.NOTICE(
                f"Generating {total_count:,} users in batches of {batch_size:,}..."
            )
        )

        stored_indexes = {}
        if not skip_optimization:
            self.stdout.write(self.style.NOTICE("Optimizing PostgreSQL for bulk insert..."))
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

        start_time = time.perf_counter()

        try:
            user_generator = UserGenerator(batch_size=batch_size)
            user_generator.generate_users(
                total_count=total_count,
                email_domain=email_domain,
                raw_password=password
            )
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

        total_time = time.perf_counter() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f"User generation completed successfully. Total time: {total_time:.3f}s"
            )
        )

        users_per_second = total_count / total_time if total_time > 0 else 0
        self.stdout.write(
            self.style.NOTICE(
                f"Performance: {users_per_second:.1f} users/second"
            )
        )
