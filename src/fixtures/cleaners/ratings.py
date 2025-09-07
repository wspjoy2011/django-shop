import contextlib
from typing import List

from django.db import transaction, connection, models
from django.db.models.signals import post_save, post_delete
from tqdm import tqdm

from apps.catalog.models import Product
from apps.ratings.models import Rating, Dislike, Like
from apps.ratings.signals import rating_saved, rating_deleted
from fixtures.signal_manager import SignalManager


class RatingsCleaner:

    def __init__(self, ratings_only: bool = False, likes_only: bool = False, dislikes_only: bool = False):
        self.ratings_only = ratings_only
        self.likes_only = likes_only
        self.dislikes_only = dislikes_only

        delete_all = not (ratings_only or likes_only or dislikes_only)

        self._models_to_clean: List[type[models.Model]] = []

        if delete_all or self.ratings_only:
            self._models_to_clean.append(Rating)
        if delete_all or self.likes_only:
            self._models_to_clean.append(Like)
        if delete_all or self.dislikes_only:
            self._models_to_clean.append(Dislike)

    def clean(self) -> None:
        if not self._models_to_clean:
            tqdm.write("RatingsCleaner: Nothing to clean.")
            return

        signals_to_disable = [
            (post_save, rating_saved, Rating),
            (post_delete, rating_deleted, Rating),
        ]

        is_rating_in_plan = Rating in self._models_to_clean
        manager = SignalManager(signals_to_disable) if is_rating_in_plan else contextlib.nullcontext()

        if is_rating_in_plan:
            tqdm.write("Temporarily disabling rating signals for bulk deletion...")

        with manager, transaction.atomic(), connection.cursor() as cursor:
            for model_cls in tqdm(self._models_to_clean, desc="Cleaning ratings tables with TRUNCATE"):
                table_name = model_cls._meta.db_table
                tqdm.write(f"Executing TRUNCATE on table: {table_name}")
                cursor.execute(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE;')
                tqdm.write(f"Table '{table_name}' truncated successfully.")

            if is_rating_in_plan:
                product_table_name = Product._meta.db_table
                tqdm.write(f"Resetting rating counters on table: {product_table_name}")
                cursor.execute(
                    f'UPDATE "{product_table_name}" SET "ratings_sum" = 0, "ratings_count" = 0 WHERE "ratings_count" > 0;'
                )
                tqdm.write(f"Rating counters on '{product_table_name}' reset successfully.")

        if is_rating_in_plan:
            tqdm.write("Rating signals have been re-enabled.")
