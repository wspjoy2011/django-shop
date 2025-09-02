import random
from typing import List, Tuple
from contextlib import nullcontext

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from apps.catalog.models import Product
from apps.ratings.models import Rating, Like, Dislike

User = get_user_model()


class RatingsGenerator:

    def __init__(self, batch_size: int = 20000, use_transaction_per_batch: bool = True):
        self.batch_size = batch_size
        self.use_transaction_per_batch = use_transaction_per_batch

        self.ARCHETYPES = {
            "banger": [1, 3, 10, 36, 50],
            "average": [3, 7, 25, 40, 25],
            "polarizing": [15, 10, 15, 20, 40],
            "stinker": [35, 25, 20, 12, 8],
        }
        self.ARCH_NAMES = ["banger", "average", "polarizing", "stinker"]
        self.ARCH_WEIGHTS = [15, 55, 15, 15]

        self.STARS = [1, 2, 3, 4, 5]

    @staticmethod
    def _jitter(dist: List[int], eps: float = 0.08) -> List[float]:
        jittered = []
        for x in dist:
            factor = 1.0 + random.uniform(-eps, eps)
            jittered.append(max(1e-6, x * factor))

        s = sum(jittered)
        return [x / s for x in jittered]

    def _pick_profile(self) -> List[float]:
        archetype = random.choices(self.ARCH_NAMES, weights=self.ARCH_WEIGHTS, k=1)[0]
        base = self.ARCHETYPES[archetype]
        return self._jitter(base, eps=0.08)

    def generate_all_ratings(
            self,
            products_coverage_percent: float = 80.0,
            ratings_per_product_range: Tuple[int, int] = (50, 500),
            likes_per_product_range: Tuple[int, int] = (20, 200),
            dislikes_per_product_range: Tuple[int, int] = (5, 50)
    ) -> None:
        print(f"Fast generating ratings for {products_coverage_percent}% products coverage...")

        all_user_ids = list(User.objects.values_list('id', flat=True))
        all_product_ids = list(Product.objects.values_list('id', flat=True))

        print(f"Found {len(all_user_ids):,} users and {len(all_product_ids):,} products")

        products_to_cover_count = int(len(all_product_ids) * products_coverage_percent / 100)
        selected_product_ids = random.sample(all_product_ids, products_to_cover_count)

        print(f"Selected {len(selected_product_ids):,} products for coverage")

        shuffled_user_ids = all_user_ids[:]
        random.shuffle(shuffled_user_ids)

        current_time = timezone.now()

        print("Generating product profiles...")
        product_profiles = {}
        for product_id in selected_product_ids:
            product_profiles[product_id] = self._pick_profile()

        self._generate_ratings_optimized(
            selected_product_ids, shuffled_user_ids, ratings_per_product_range, current_time, product_profiles
        )
        self._generate_likes_dislikes_optimized(
            selected_product_ids, shuffled_user_ids,
            likes_per_product_range, dislikes_per_product_range, current_time, product_profiles
        )

        print("All ratings generation completed successfully!")

    def _generate_ratings_optimized(
            self,
            product_ids: List[int],
            shuffled_user_ids: List[int],
            ratings_per_product_range: Tuple[int, int],
            current_time,
            product_profiles: dict
    ) -> None:
        print(f"Generating ratings for {len(product_ids):,} products...")

        ratings_batch = []
        user_offset = 0
        total_users = len(shuffled_user_ids)

        append_rating = ratings_batch.append
        bulk_limit = self.batch_size
        bulk_create = self._bulk_create_ratings

        progress_bar = tqdm(product_ids, desc="Generating ratings")

        for product_id in progress_bar:
            ratings_count = random.randint(*ratings_per_product_range)

            selected_user_ids = self._get_users_sliding_window(
                shuffled_user_ids, user_offset, ratings_count, total_users
            )
            user_offset = (user_offset + ratings_count) % total_users

            weights = product_profiles[product_id]
            scores = random.choices(self.STARS, weights=weights, k=len(selected_user_ids))

            for user_id, score in zip(selected_user_ids, scores):
                append_rating(Rating(
                    user_id=user_id,
                    product_id=product_id,
                    score=score,
                    created_at=current_time,
                    updated_at=current_time
                ))

                if len(ratings_batch) >= bulk_limit:
                    bulk_create(ratings_batch)
                    ratings_batch.clear()

        if ratings_batch:
            bulk_create(ratings_batch)

        print(f"Created ratings for {len(product_ids):,} products")

    def _generate_likes_dislikes_optimized(
            self,
            product_ids: List[int],
            shuffled_user_ids: List[int],
            likes_per_product_range: Tuple[int, int],
            dislikes_per_product_range: Tuple[int, int],
            current_time,
            product_profiles: dict
    ) -> None:
        print(f"Generating likes and dislikes for {len(product_ids):,} products...")

        likes_batch = []
        dislikes_batch = []
        user_offset = 0
        total_users = len(shuffled_user_ids)

        append_like = likes_batch.append
        append_dislike = dislikes_batch.append
        bulk_limit = self.batch_size
        bulk_create_likes = self._bulk_create_likes
        bulk_create_dislikes = self._bulk_create_dislikes

        progress_bar = tqdm(product_ids, desc="Generating likes/dislikes")

        for product_id in progress_bar:
            weights = product_profiles[product_id]
            expected_rating = sum(star * weight for star, weight in zip(self.STARS, weights))

            positivity = (expected_rating - 1.0) / 4.0

            likes_min, likes_max = likes_per_product_range
            dislikes_min, dislikes_max = dislikes_per_product_range

            likes_target = int(likes_min + positivity * (likes_max - likes_min))
            dislikes_target = int(dislikes_max - positivity * (dislikes_max - dislikes_min))

            likes_noise = int(likes_target * 0.1)
            dislikes_noise = int(dislikes_target * 0.1)

            likes_count = max(0, random.randint(
                max(0, likes_target - likes_noise),
                likes_target + likes_noise
            ))
            dislikes_count = max(0, random.randint(
                max(0, dislikes_target - dislikes_noise),
                dislikes_target + dislikes_noise
            ))

            total_interactions = likes_count + dislikes_count

            if total_interactions == 0:
                continue

            selected_user_ids = self._get_users_sliding_window(
                shuffled_user_ids, user_offset, total_interactions, total_users
            )
            user_offset = (user_offset + total_interactions) % total_users

            likes_user_ids = selected_user_ids[:likes_count]
            dislikes_user_ids = selected_user_ids[likes_count:likes_count + dislikes_count]

            for user_id in likes_user_ids:
                append_like(Like(
                    user_id=user_id,
                    product_id=product_id,
                    created_at=current_time
                ))

            for user_id in dislikes_user_ids:
                append_dislike(Dislike(
                    user_id=user_id,
                    product_id=product_id,
                    created_at=current_time
                ))

            if len(likes_batch) >= bulk_limit:
                bulk_create_likes(likes_batch)
                likes_batch.clear()

            if len(dislikes_batch) >= bulk_limit:
                bulk_create_dislikes(dislikes_batch)
                dislikes_batch.clear()

        if likes_batch:
            bulk_create_likes(likes_batch)
        if dislikes_batch:
            bulk_create_dislikes(dislikes_batch)

        print(f"Created likes and dislikes for {len(product_ids):,} products")

    @staticmethod
    def _get_users_sliding_window(
            shuffled_user_ids: List[int],
            offset: int,
            count: int,
            total_users: int
    ) -> List[int]:
        if count >= total_users:
            return shuffled_user_ids[:]

        if offset + count <= total_users:
            return shuffled_user_ids[offset:offset + count]
        else:
            return shuffled_user_ids[offset:] + shuffled_user_ids[:(offset + count) % total_users]

    def _bulk_create_ratings(self, ratings_batch: List[Rating]) -> None:
        transaction_context = transaction.atomic() if self.use_transaction_per_batch else nullcontext()
        with transaction_context:
            Rating.objects.bulk_create(
                ratings_batch,
                batch_size=self.batch_size,
                ignore_conflicts=True
            )

    def _bulk_create_likes(self, likes_batch: List[Like]) -> None:
        transaction_context = transaction.atomic() if self.use_transaction_per_batch else nullcontext()
        with transaction_context:
            Like.objects.bulk_create(
                likes_batch,
                batch_size=self.batch_size,
                ignore_conflicts=True
            )

    def _bulk_create_dislikes(self, dislikes_batch: List[Dislike]) -> None:
        transaction_context = transaction.atomic() if self.use_transaction_per_batch else nullcontext()
        with transaction_context:
            Dislike.objects.bulk_create(
                dislikes_batch,
                batch_size=self.batch_size,
                ignore_conflicts=True
            )

    @staticmethod
    def get_statistics() -> dict:
        return {
            'total_ratings': Rating.objects.count(),
            'total_likes': Like.objects.count(),
            'total_dislikes': Dislike.objects.count(),
            'products_with_ratings': Rating.objects.values('product').distinct().count(),
            'products_with_likes': Like.objects.values('product').distinct().count(),
            'products_with_dislikes': Dislike.objects.values('product').distinct().count(),
        }
