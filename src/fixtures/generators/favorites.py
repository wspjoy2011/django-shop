import random
from typing import List

from django.contrib.auth import get_user_model
from django.db import connection
from django.utils.text import slugify
from django.utils import timezone
from tqdm import tqdm

from apps.catalog.models import Product
from apps.favorites.models import FavoriteCollection, FavoriteItem
from fixtures.utils import copy_insert_data

User = get_user_model()



class FavoriteCollectionsGenerator:

    def select_users_and_create_collections(self, percentage: float = 30.0) -> List[int]:
        users_without_collections = list(User.objects.filter(
            favorite_collections__isnull=True
        ).exclude(is_superuser=True).values_list('id', 'username'))

        if not users_without_collections:
            print("All non-superuser users already have favorite collections.")
            return []

        selected_count = max(1, int(len(users_without_collections) * percentage / 100))
        selected_users = random.sample(users_without_collections, selected_count)

        print(f"Selected {len(selected_users):,} users to receive a default favorite collection.")

        collections_data = []
        user_ids = []
        current_time = timezone.now()
        for user_id, username in tqdm(selected_users, desc="Preparing collections"):
            collection_name = 'My favorites'
            generated_slug = slugify(f"{username}-{collection_name}")

            collections_data.append((
                user_id,
                collection_name,
                generated_slug,
                'Default favorite collection',
                True,
                False,
                current_time,
                current_time,
            ))
            user_ids.append(user_id)

        copy_insert_data(
            FavoriteCollection,
            ['user_id', 'name', 'slug', 'description', 'is_default', 'is_public', 'created_at', 'updated_at'],
            collections_data
        )

        print(f"Created default collections for {len(user_ids)} users.")
        return user_ids

    @staticmethod
    def clear_all_collections_except_admin() -> None:
        print("Clearing all collections except for superusers...")
        with connection.cursor() as cursor:
            cursor.execute("""
                           DELETE
                           FROM favorites_favoritecollection
                           WHERE user_id NOT IN (SELECT id FROM accounts_user WHERE is_superuser = TRUE);
                           """)
            print(f"{cursor.rowcount} collections deleted.")


class FavoriteItemsGenerator:

    def generate_for_users(
            self,
            user_ids: List[int],
            min_items: int = 10,
            max_items: int = 50
    ) -> None:
        if not user_ids:
            print("No user IDs provided for favorite item generation.")
            return

        all_products = list(Product.objects.values_list('id', flat=True))
        if not all_products:
            print("No products found to add to favorites.")
            return

        favorite_items_data = []
        notes = [
            "Love this item!", "Want to buy later", "Great quality",
            "Perfect for summer", "Gift idea", "Waiting for sale",
            "Favorite color", "Must have",
        ]
        current_time = timezone.now()

        collections = list(FavoriteCollection.objects.filter(
            user_id__in=user_ids,
            is_default=True
        ).values_list('id', flat=True))

        for collection_id in tqdm(collections, desc="Preparing favorite items"):
            items_count = random.randint(min_items, max_items)
            selected_products = random.sample(all_products, min(items_count, len(all_products)))

            for position, product_id in enumerate(selected_products, start=1):
                note = ""
                if random.random() < 0.1:
                    note = random.choice(notes)

                favorite_items_data.append((
                    collection_id,
                    product_id,
                    position,
                    note,
                    current_time
                ))

        print(f"Generated {len(favorite_items_data):,} favorite items to be inserted.")
        copy_insert_data(
            FavoriteItem,
            ['collection_id', 'product_id', 'position', 'note', 'created_at'],
            favorite_items_data
        )

    @staticmethod
    def clear_all_items_except_admin() -> None:
        print("Clearing all favorite items except for superusers...")
        with connection.cursor() as cursor:
            cursor.execute("""
                           DELETE
                           FROM favorites_favoriteitem
                           WHERE collection_id IN (SELECT id
                                                   FROM favorites_favoritecollection
                                                   WHERE user_id NOT IN (SELECT id FROM accounts_user WHERE is_superuser = TRUE));
                           """)
            print(f"{cursor.rowcount} favorite items deleted.")
