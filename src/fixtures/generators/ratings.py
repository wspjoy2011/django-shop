import random
import time
from typing import List, Tuple
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db import transaction, connection, models
from django.db.models.signals import post_save, post_delete
from django.utils import timezone
from tqdm import tqdm

from apps.catalog.models import Product
from apps.ratings.models import Rating, Like, Dislike
from apps.ratings.signals import rating_saved, rating_deleted
from fixtures.signal_manager import SignalManager

User = get_user_model()


class RatingsGenerator:

    def __init__(self, batch_size: int = 50000):
        self.batch_size = batch_size
        self.ARCHETYPES = {
            "banger": [1, 3, 10, 36, 50],
            "average": [3, 7, 25, 40, 25],
            "polarizing": [15, 10, 15, 20, 40],
            "stinker": [35, 25, 20, 12, 8],
        }
        self.STARS = [1, 2, 3, 4, 5]

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
        product_profiles = {pid: self._pick_profile() for pid in selected_product_ids}

        signals_to_disable = [(post_save, rating_saved, Rating), (post_delete, rating_deleted, Rating)]
        print("Temporarily disabling rating signals for bulk creation...")
        with SignalManager(signals_to_disable):
            product_stats, ratings_data = self._prepare_ratings_data(
                selected_product_ids, shuffled_user_ids, ratings_per_product_range, current_time, product_profiles
            )
            self._copy_insert_data(Rating, ['user_id', 'product_id', 'score', 'created_at', 'updated_at'], ratings_data)

            likes_data, dislikes_data = self._prepare_likes_dislikes_data(
                selected_product_ids, shuffled_user_ids, likes_per_product_range, dislikes_per_product_range,
                current_time, product_profiles
            )
            self._copy_insert_data(Like, ['user_id', 'product_id', 'created_at'], likes_data)
            self._copy_insert_data(Dislike, ['user_id', 'product_id', 'created_at'], dislikes_data)

        print("Rating signals have been re-enabled.")

        if product_stats:
            print(f"Updating rating statistics for {len(product_stats)} products...")
            self._bulk_update_product_stats(product_stats)
        print("All ratings generation completed successfully!")

    @staticmethod
    def _copy_insert_data(model: type[models.Model], columns: List[str], data: List[tuple]):
        if not data:
            print(f"No data to insert for {model._meta.object_name}. Skipping.")
            return

        table_name = model._meta.db_table
        temp_table_name = f"temp_copy_{table_name}"

        column_defs = []
        for col_name in columns:
            field = model._meta.get_field(col_name)
            if isinstance(field, (models.ForeignKey, models.IntegerField, models.PositiveSmallIntegerField)):
                column_defs.append(f"{col_name} integer")
            elif isinstance(field, models.DateTimeField):
                column_defs.append(f"{col_name} timestamp with time zone")

        print(f"Starting native COPY insert for {len(data):,} rows into '{table_name}'...")
        start_time = time.perf_counter()

        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f"CREATE TEMP TABLE {temp_table_name} ({', '.join(column_defs)}) ON COMMIT DROP;")

            sql_copy = f"COPY {temp_table_name} ({', '.join(columns)}) FROM STDIN"
            with cursor.copy(sql_copy) as copy:
                for row in data:
                    copy.write_row(row)

            cursor.execute(f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                SELECT {', '.join(columns)} FROM {temp_table_name};
            """)
            inserted_rows = cursor.rowcount

        end_time = time.perf_counter()
        print(
            f"COPY insert for '{table_name}' complete. Inserted {inserted_rows:,} rows in {end_time - start_time:.3f}s.")

    def _prepare_ratings_data(self, product_ids, shuffled_user_ids, ratings_range, current_time, profiles):
        print(f"Preparing data for {len(product_ids):,} products' ratings...")
        ratings_data = []
        product_stats = defaultdict(lambda: {'sum': 0, 'count': 0})
        user_offset = 0
        total_users = len(shuffled_user_ids)

        for product_id in tqdm(product_ids, desc="Preparing ratings data"):
            count = random.randint(*ratings_range)
            users = self._get_users_sliding_window(shuffled_user_ids, user_offset, count, total_users)
            user_offset = (user_offset + count) % total_users
            scores = random.choices(self.STARS, weights=profiles[product_id], k=len(users))

            for user_id, score in zip(users, scores):
                ratings_data.append((user_id, product_id, score, current_time, current_time))
                product_stats[product_id]['sum'] += score
                product_stats[product_id]['count'] += 1

        return product_stats, ratings_data

    def _prepare_likes_dislikes_data(self, product_ids, shuffled_user_ids, likes_range, dislikes_range, current_time,
                                     profiles):
        print(f"Preparing data for {len(product_ids):,} products' likes/dislikes...")
        likes_data, dislikes_data = [], []
        user_offset = 0
        total_users = len(shuffled_user_ids)

        for product_id in tqdm(product_ids, desc="Preparing likes/dislikes data"):
            positivity = (sum(s * w for s, w in zip(self.STARS, profiles[product_id])) - 1.0) / 4.0
            likes_target = int(likes_range[0] + positivity * (likes_range[1] - likes_range[0]))
            dislikes_target = int(dislikes_range[1] - positivity * (dislikes_range[1] - dislikes_range[0]))

            likes_count = max(0, random.randint(int(likes_target * 0.9), int(likes_target * 1.1)))
            dislikes_count = max(0, random.randint(int(dislikes_target * 0.9), int(dislikes_target * 1.1)))

            if (likes_count + dislikes_count) == 0: continue

            users = self._get_users_sliding_window(shuffled_user_ids, user_offset, likes_count + dislikes_count,
                                                   total_users)
            user_offset = (user_offset + likes_count + dislikes_count) % total_users

            for i, user_id in enumerate(users):
                (likes_data if i < likes_count else dislikes_data).append((user_id, product_id, current_time))

        return likes_data, dislikes_data

    @staticmethod
    def _bulk_update_product_stats(product_stats: dict):
        if not product_stats or connection.vendor != 'postgresql':
            return

        table_name = Product._meta.db_table
        temp_table_name = f"temp_stats_{table_name}"
        data_to_update = [(pid, stats['sum'], stats['count']) for pid, stats in product_stats.items()]

        print(
            f"Starting optimized bulk update for {len(data_to_update):,} products using raw SQL (COPY & UPDATE FROM)...")
        start_time = time.perf_counter()

        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                f"CREATE TEMP TABLE {temp_table_name} (id integer PRIMARY KEY, ratings_sum integer, ratings_count integer) ON COMMIT DROP;")
            sql_copy = f"COPY {temp_table_name} (id, ratings_sum, ratings_count) FROM STDIN"
            with cursor.copy(sql_copy) as copy:
                for row in data_to_update:
                    copy.write_row(row)
            cursor.execute(
                f"UPDATE {table_name} AS main SET ratings_sum = temp.ratings_sum, ratings_count = temp.ratings_count FROM {temp_table_name} AS temp WHERE main.id = temp.id;")

        end_time = time.perf_counter()
        print(f"Optimized bulk update finished in {end_time - start_time:.3f} seconds.")

    @staticmethod
    def _get_users_sliding_window(shuffled_user_ids: List[int], offset: int, count: int, total_users: int) -> List[int]:
        if count >= total_users: return shuffled_user_ids[:]
        if offset + count <= total_users: return shuffled_user_ids[offset:offset + count]
        return shuffled_user_ids[offset:] + shuffled_user_ids[:(offset + count) % total_users]

    def _pick_profile(self) -> List[float]:
        archetype = random.choices(list(self.ARCHETYPES.keys()), weights=[15, 55, 15, 15], k=1)[0]
        base = self.ARCHETYPES[archetype]
        jittered = [max(1e-6, x * (1.0 + random.uniform(-0.08, 0.08))) for x in base]
        s = sum(jittered)
        return [x / s for x in jittered]

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
