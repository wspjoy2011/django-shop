import time

from django.core.management.base import BaseCommand

from apps.catalog.models import Product
from apps.ratings.models import Rating, Like, Dislike

from fixtures.cleaners.ratings import RatingsCleaner
from fixtures.db_tuning import optimize_postgresql_for_bulk_operations, restore_postgresql_after_bulk_operations


class Command(BaseCommand):
    help = "Clear all ratings, likes and dislikes data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            dest="yes",
            help="Do not prompt for confirmation.",
        )
        parser.add_argument(
            "--ratings-only",
            action="store_true",
            dest="ratings_only",
            help="Delete only ratings (keep likes and dislikes).",
        )
        parser.add_argument(
            "--likes-only",
            action="store_true",
            dest="likes_only",
            help="Delete only likes (keep ratings and dislikes).",
        )
        parser.add_argument(
            "--dislikes-only",
            action="store_true",
            dest="dislikes_only",
            help="Delete only dislikes (keep ratings and likes).",
        )
        parser.add_argument(
            "--skip-optimization",
            action="store_true",
            dest="skip_optimization",
            default=False,
            help="Do not drop indexes or apply PostgreSQL optimizations.",
        )

    def handle(self, *args, **options):
        ratings_count = Rating.objects.count()
        likes_count = Like.objects.count()
        dislikes_count = Dislike.objects.count()
        products_with_ratings = Product.objects.filter(ratings_count__gt=0).count()
        total_count = ratings_count + likes_count + dislikes_count + products_with_ratings

        self.stdout.write(
            self.style.NOTICE(
                f"Current state:\n"
                f"  Ratings: {ratings_count:,}\n"
                f"  Likes: {likes_count:,}\n"
                f"  Dislikes: {dislikes_count:,}\n"
                f"  Products with ratings: {products_with_ratings:,}\n"
                f"  Total records: {total_count:,}"
            )
        )

        if total_count == 0:
            self.stdout.write(self.style.WARNING("No ratings data to delete."))
            return

        ratings_only = options["ratings_only"]
        likes_only = options["likes_only"]
        dislikes_only = options["dislikes_only"]

        items_to_delete = []
        if not (ratings_only or likes_only or dislikes_only):
            items_to_delete = ["Ratings", "Likes", "Dislikes"]
        else:
            if ratings_only:
                items_to_delete.append("Ratings")
            if likes_only:
                items_to_delete.append("Likes")
            if dislikes_only:
                items_to_delete.append("Dislikes")

        confirmed = options["yes"]
        if not confirmed:
            items_text = ", ".join(items_to_delete)
            answer = input(
                f"This will DELETE all {items_text}. "
                "Are you sure? Type 'yes' to continue: "
            )
            if answer.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        stored_indexes = {}
        if not options["skip_optimization"]:
            self.stdout.write(self.style.NOTICE("Optimizing PostgreSQL for bulk deletion..."))
            t0 = time.perf_counter()
            table_names = ['ratings_rating', 'ratings_like', 'ratings_dislike']
            stored_indexes, drop_results = optimize_postgresql_for_bulk_operations(table_names)
            ok = sum(1 for v in drop_results.values() if v)
            fail = sum(1 for v in drop_results.values() if not v)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Optimization complete: {ok} indexes dropped, {fail} failed in {time.perf_counter() - t0:.3f}s"
                )
            )

        self.stdout.write(self.style.NOTICE("Clearing ratings data..."))
        start_time = time.perf_counter()

        try:
            cleaner = RatingsCleaner(
                ratings_only=options["ratings_only"],
                likes_only=options["likes_only"],
                dislikes_only=options["dislikes_only"],
            )
            cleaner.clean()
        finally:
            if not options["skip_optimization"] and stored_indexes:
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

        total_time = time.perf_counter() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f"Ratings cleanup completed in {total_time:.3f}s."
            )
        )

        final_ratings = Rating.objects.count()
        final_likes = Like.objects.count()
        final_dislikes = Dislike.objects.count()
        final_products_with_ratings = Product.objects.filter(ratings_count__gt=0).count()
        final_total = final_ratings + final_likes + final_dislikes + final_products_with_ratings

        self.stdout.write(
            self.style.NOTICE(
                f"Final state:\n"
                f"  Ratings: {final_ratings:,}\n"
                f"  Likes: {final_likes:,}\n"
                f"  Dislikes: {final_dislikes:,}\n"
                f"  Products with ratings: {final_products_with_ratings:,}\n"
                f"  Total: {final_total:,}"
            )
        )
