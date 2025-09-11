from django.core.management.base import BaseCommand
from django.db import OperationalError, DatabaseError

from apps.catalog.pgviews import PriceRangesMV, GenderFilterOptionsMV


class Command(BaseCommand):
    help = "Refreshes all materialized views in the project."

    def handle(self, *args, **options):
        views_to_refresh = [PriceRangesMV, GenderFilterOptionsMV]

        self.stdout.write(
            self.style.NOTICE(f"Attempting to refresh {len(views_to_refresh)} materialized view(s)...")
        )

        for view_model in views_to_refresh:
            view_name = view_model._meta.db_table
            self.stdout.write(f"- Refreshing {view_name}...", ending="")

            try:
                view_model.refresh(concurrently=True)
                self.stdout.write(self.style.SUCCESS(" Done."))
            except (OperationalError, DatabaseError) as e:
                self.stderr.write(self.style.ERROR(f"\nFailed to refresh {view_name}: {e}"))
                self.stderr.write(
                    "  Please ensure the view and its concurrent index exist. "
                    "Have you run `python manage.py sync_pgviews --force`?"
                )
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"\nAn unexpected error occurred while refreshing {view_name}: {e}")
                )

        self.stdout.write(self.style.SUCCESS("\nMaterialized views refresh process completed."))
