import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from fixtures.cleaners.users import UserCleaner

User = get_user_model()


class Command(BaseCommand):
    help = "Clear user data (deletes all users except 'admin')."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            dest="yes",
            help="Do not prompt for confirmation.",
        )

    def handle(self, *args, **options):
        current_users = User.objects.count()
        admin_users = User.objects.filter(username="admin").count()
        users_to_delete = current_users - admin_users

        self.stdout.write(
            self.style.NOTICE(
                f"Current users: {current_users:,} total, {admin_users} admin(s), "
                f"{users_to_delete:,} will be deleted"
            )
        )

        if users_to_delete == 0:
            self.stdout.write(self.style.WARNING("No users to delete."))
            return

        confirmed = options["yes"]
        if not confirmed:
            answer = input(
                f"This will DELETE {users_to_delete:,} users (keeping admin). "
                "Are you sure? Type 'yes' to continue: "
            )
            if answer.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        self.stdout.write(self.style.NOTICE("Clearing user data..."))
        start = time.perf_counter()

        cleaner = UserCleaner()
        cleaner.clean()

        total_time = time.perf_counter() - start

        remaining_users = User.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Users cleared in {total_time:.3f}s. "
                f"Remaining users: {remaining_users:,}"
            )
        )
