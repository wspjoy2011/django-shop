import time

from django.core.management.base import BaseCommand

from fixtures.generators.users import UserGenerator


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

    def handle(self, *args, **options):
        total_count = options["count"]
        batch_size = options["batch_size"]
        password = options["password"]
        email_domain = options["email_domain"]

        self.stdout.write(
            self.style.NOTICE(
                f"Generating {total_count:,} users in batches of {batch_size:,}..."
            )
        )

        start_time = time.perf_counter()

        user_generator = UserGenerator(batch_size=batch_size)
        user_generator.generate_users(
            total_count=total_count,
            email_domain=email_domain,
            raw_password=password
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
