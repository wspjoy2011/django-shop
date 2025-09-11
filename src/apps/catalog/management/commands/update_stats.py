from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import ProgrammingError, DatabaseError

from fixtures.utils import analyze_table


class Command(BaseCommand):
    help = "Updates PostgreSQL statistics for all tables in specified project apps."

    APP_LABELS_TO_ANALYZE = [
        'accounts',
        'rest',
        'catalog',
        'inventories',
        'favorites',
        'ratings',
    ]

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Starting PostgreSQL ANALYZE for project tables...")
        )

        for app_label in self.APP_LABELS_TO_ANALYZE:
            try:
                app_config = apps.get_app_config(app_label)
                self.stdout.write(f"\n--- Analyzing app: {app_config.verbose_name} ({app_label}) ---")

                models_to_analyze = app_config.get_models()
                if not models_to_analyze:
                    self.stdout.write(self.style.WARNING(f"No models found in app '{app_label}'."))
                    continue

                for model in models_to_analyze:
                    self.stdout.write(
                        f"Analyzing table for model '{model._meta.verbose_name_plural}' ({model._meta.db_table})...",
                        ending=""
                    )
                    try:
                        analyze_table(model)
                        self.stdout.write(self.style.SUCCESS(" Done."))
                    except (ProgrammingError, DatabaseError) as e:
                        self.stdout.write(self.style.ERROR(f" Failed (maybe no table exists?): {e}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f" An unexpected error occurred: {e}"))

            except LookupError:
                self.stdout.write(self.style.ERROR(f"App with label '{app_label}' not found. Skipping."))

        self.stdout.write(
            self.style.SUCCESS("\nPostgreSQL statistics update complete.")
        )
