import time

from django.core.management.base import BaseCommand

from fixtures.generators.favorites import FavoriteCollectionsGenerator, FavoriteItemsGenerator


class Command(BaseCommand):
    help = "Clear favorites data (deletes FavoriteItems and FavoriteCollections except for admin user)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            dest="yes",
            help="Do not prompt for confirmation.",
        )
        parser.add_argument(
            "--items-only",
            action="store_true",
            dest="items_only",
            help="Delete only favorite items, keep collections.",
        )
        parser.add_argument(
            "--collections-only",
            action="store_true",
            dest="collections_only",
            help="Delete only collections (and their items).",
        )

    def handle(self, *args, **options):
        confirmed = options["yes"]
        items_only = options["items_only"]
        collections_only = options["collections_only"]

        if items_only and collections_only:
            self.stdout.write(
                self.style.ERROR("Cannot use both --items-only and --collections-only")
            )
            return

        if items_only:
            delete_message = "This will DELETE all favorite items (except for admin user)."
        elif collections_only:
            delete_message = "This will DELETE all favorite collections and their items (except for admin user)."
        else:
            delete_message = "This will DELETE all favorites data - collections and items (except for admin user)."

        if not confirmed:
            answer = input(
                f"{delete_message} Are you sure? Type 'yes' to continue: "
            )
            if answer.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        total_start = time.perf_counter()

        if not collections_only:
            self.stdout.write(self.style.NOTICE("Clearing favorite items..."))
            items_start = time.perf_counter()

            items_generator = FavoriteItemsGenerator()
            items_generator.clear_all_items_except_admin()

            items_time = time.perf_counter() - items_start
            self.stdout.write(
                self.style.SUCCESS(f"Favorite items cleared in {items_time:.3f}s")
            )

        if not items_only:
            self.stdout.write(self.style.NOTICE("Clearing favorite collections..."))
            collections_start = time.perf_counter()

            collections_generator = FavoriteCollectionsGenerator()
            collections_generator.clear_all_collections_except_admin()

            collections_time = time.perf_counter() - collections_start
            self.stdout.write(
                self.style.SUCCESS(f"Favorite collections cleared in {collections_time:.3f}s")
            )

        total_time = time.perf_counter() - total_start
        self.stdout.write(
            self.style.SUCCESS(f"Favorites cleared in {total_time:.3f}s")
        )
