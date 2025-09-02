import time

from django.core.management.base import BaseCommand

from etl.cleaner import DjangoCatalogCleaner


class Command(BaseCommand):
    help = "Clear catalog data (deletes Products, ArticleTypes, SubCategories, MasterCategories, BaseColours, Seasons, UsageTypes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            dest="yes",
            help="Do not prompt for confirmation.",
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

        self.stdout.write(self.style.NOTICE("Clearing catalog tables..."))
        start = time.perf_counter()

        cleaner = DjangoCatalogCleaner()
        cleaner.clean()

        total = time.perf_counter() - start
        self.stdout.write(self.style.SUCCESS(f"Catalog cleared in {total:.3f}s"))
