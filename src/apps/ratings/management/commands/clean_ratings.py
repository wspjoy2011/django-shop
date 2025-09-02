import time

from django.core.management.base import BaseCommand
from apps.ratings.models import Rating, Like, Dislike

from fixtures.cleaners.ratings import RatingsCleaner


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

    def handle(self, *args, **options):
        ratings_count = Rating.objects.count()
        likes_count = Like.objects.count()
        dislikes_count = Dislike.objects.count()
        total_count = ratings_count + likes_count + dislikes_count

        self.stdout.write(
            self.style.NOTICE(
                f"Current state:\n"
                f"  Ratings: {ratings_count:,}\n"
                f"  Likes: {likes_count:,}\n"
                f"  Dislikes: {dislikes_count:,}\n"
                f"  Total: {total_count:,}"
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

        self.stdout.write(self.style.NOTICE("Clearing ratings data..."))
        start_time = time.perf_counter()

        cleaner = RatingsCleaner(
            ratings_only=ratings_only,
            likes_only=likes_only,
            dislikes_only=dislikes_only
        )
        cleaner.clean()

        total_time = time.perf_counter() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f"Ratings cleanup completed in {total_time:.3f}s."
            )
        )

        final_ratings = Rating.objects.count()
        final_likes = Like.objects.count()
        final_dislikes = Dislike.objects.count()
        final_total = final_ratings + final_likes + final_dislikes

        self.stdout.write(
            self.style.NOTICE(
                f"Final state:\n"
                f"  Ratings: {final_ratings:,}\n"
                f"  Likes: {final_likes:,}\n"
                f"  Dislikes: {final_dislikes:,}\n"
                f"  Total: {final_total:,}"
            )
        )
