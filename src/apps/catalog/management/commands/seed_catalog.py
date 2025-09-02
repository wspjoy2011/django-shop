import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from etl.extract_transform import CatalogCSVExtractTransformer
from etl.load import DjangoCatalogSeeder


class Command(BaseCommand):
    help = "Seed catalog data from CSV files into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--products",
            dest="products_csv",
            type=str,
            default=str(getattr(settings, "PRODUCTS_DATASET_CSV", "")),
            help="Path to products CSV file (defaults to settings.PRODUCTS_DATASET_CSV)",
        )
        parser.add_argument(
            "--images",
            dest="images_csv",
            type=str,
            default=str(getattr(settings, "IMAGES_DATASET_CSV", "")),
            help="Path to images CSV file (defaults to settings.IMAGES_DATASET_CSV)",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=5000,
            help="Bulk insert batch size for seeding (default: 5000)",
        )

    def handle(self, *args, **options):
        products_csv = options["products_csv"]
        images_csv = options["images_csv"]
        batch_size = options["batch_size"]

        if not products_csv:
            raise CommandError("Path to products CSV is not provided and settings.PRODUCTS_DATASET_CSV is empty.")
        if not images_csv:
            raise CommandError("Path to images CSV is not provided and settings.IMAGES_DATASET_CSV is empty.")

        products_path = Path(products_csv)
        images_path = Path(images_csv)

        if not products_path.exists():
            raise CommandError(f"Products CSV not found: {products_path}")
        if not images_path.exists():
            raise CommandError(f"Images CSV not found: {images_path}")

        total_start = time.perf_counter()

        self.stdout.write(self.style.NOTICE("Extracting and transforming CSV datasets..."))
        extract_start = time.perf_counter()
        etl = CatalogCSVExtractTransformer(styles_path=products_path, images_path=images_path)
        dto = etl.execute()
        extract_time = time.perf_counter() - extract_start
        self.stdout.write(self.style.SUCCESS(f"Extract+Transform done in {extract_time:.3f}s"))

        self.stdout.write(self.style.NOTICE("Seeding database via Django ORM..."))
        load_start = time.perf_counter()
        seeder = DjangoCatalogSeeder(batch_size=batch_size)
        seeder.seed(dto)
        load_time = time.perf_counter() - load_start
        self.stdout.write(self.style.SUCCESS(f"Load (seeding) done in {load_time:.3f}s"))

        total_time = time.perf_counter() - total_start
        self.stdout.write(self.style.SUCCESS(f"Seeding completed successfully. Total time: {total_time:.3f}s"))
