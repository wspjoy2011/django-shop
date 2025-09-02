from typing import List, Tuple

from django.db import transaction
from tqdm import tqdm

from apps.ratings.models import Rating, Dislike, Like


class RatingsCleaner:

    def __init__(self, ratings_only: bool = False, likes_only: bool = False, dislikes_only: bool = False):
        self.ratings_only = ratings_only
        self.likes_only = likes_only
        self.dislikes_only = dislikes_only

        delete_all = not (ratings_only or likes_only or dislikes_only)

        self._deletion_plan: List[Tuple[str, object]] = []

        if delete_all or ratings_only:
            self._deletion_plan.append(("Ratings", Rating.objects.all()))

        if delete_all or likes_only:
            self._deletion_plan.append(("Likes", Like.objects.all()))

        if delete_all or dislikes_only:
            self._deletion_plan.append(("Dislikes", Dislike.objects.all()))

    def clean(self) -> None:
        with transaction.atomic():
            for label, qs in tqdm(self._deletion_plan, desc="Cleaning ratings"):
                deleted_count, _ = qs.delete()
                tqdm.write(f"Deleted {deleted_count} rows from {label}")
