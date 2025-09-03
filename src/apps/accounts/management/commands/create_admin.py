from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import IntegrityError

User = get_user_model()


class Command(BaseCommand):
    help = "Create Django admin superuser using settings from environment variables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation even if admin already exists (will update existing user)",
        )

    def handle(self, *args, **options):
        username = settings.ADMIN_USERNAME
        password = settings.ADMIN_PASSWORD
        email = settings.ADMIN_EMAIL

        if not username:
            raise CommandError(
                "ADMIN_USERNAME environment variable is not set. "
                "Please set it in your .env file or environment."
            )

        if not password:
            raise CommandError(
                "ADMIN_PASSWORD environment variable is not set. "
                "Please set it in your .env file or environment."
            )

        if not email:
            raise CommandError(
                "ADMIN_EMAIL environment variable is not set. "
                "Please set it in your .env file or environment."
            )

        try:
            if User.objects.filter(username=username).exists():
                if options['force']:
                    user = User.objects.get(username=username)
                    user.set_password(password)
                    user.email = email
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully updated admin user "{username}"'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Admin user "{username}" already exists. '
                            'Use --force to update existing user.'
                        )
                    )
                    return

            else:
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created admin user "{username}"'
                    )
                )

        except IntegrityError as e:
            raise CommandError(f"Error creating admin user: {e}")
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}")

        self.stdout.write(
            self.style.NOTICE(
                f"Admin user details:\n"
                f"  Username: {username}\n"
                f"  Email: {email}\n"
                f"  Staff: True\n"
                f"  Superuser: True"
            )
        )
