import random
from contextlib import nullcontext
from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction
from tqdm import tqdm

from apps.catalog.models import Product
from apps.favorites.models import FavoriteCollection, FavoriteItem

User = get_user_model()


class FavoriteCollectionsGenerator:
    """Generate default favorite collections for selected percentage of users"""

    def __init__(self, batch_size: int = 10000, use_transaction_per_batch: bool = False):
        self.batch_size = batch_size
        self.use_transaction_per_batch = use_transaction_per_batch

    def select_users_and_create_collections(self, percentage: float = 30.0) -> List[int]:
        users_without_collections = list(User.objects.filter(
            favorite_collections__isnull=True
        ).exclude(username='admin').values_list('id', 'username'))

        if not users_without_collections:
            print("All users already have favorite collections")
            return []

        selected_count = max(1, int(len(users_without_collections) * percentage / 100))
        selected_users = random.sample(users_without_collections, selected_count)

        print(
            f"Selected {selected_count} users ({percentage}%) from {len(users_without_collections)}"
            f" users without collections")

        collections_batch = []
        batch_count = 0
        user_ids = []

        progress_bar = tqdm(selected_users, desc="Creating collections", unit="users")

        for user_id, username in progress_bar:
            collection = FavoriteCollection(
                user_id=user_id,
                name='My favorites',
                description='Default favorite collection',
                is_default=True,
                is_public=False,
            )
            collections_batch.append(collection)
            user_ids.append(user_id)

            if len(collections_batch) >= self.batch_size:
                self._bulk_create_collections(collections_batch)
                batch_count += 1
                progress_bar.set_postfix(batches=batch_count)
                collections_batch = []

        if collections_batch:
            self._bulk_create_collections(collections_batch)
            batch_count += 1

        print(f"Created default collections for {len(user_ids)} users in {batch_count} batches")
        return user_ids

    @staticmethod
    def clear_all_collections_except_admin() -> None:
        print("Clearing all collections except admin user...")

        collections_to_delete = FavoriteCollection.objects.exclude(user__username='admin')
        count = collections_to_delete.count()

        if count > 0:
            with tqdm(total=count, desc="Deleting collections", unit="collections") as pbar:
                batch_size = 10000
                deleted_total = 0

                while True:
                    ids_to_delete = list(collections_to_delete.values_list('id', flat=True)[:batch_size])
                    if not ids_to_delete:
                        break

                    FavoriteCollection.objects.filter(id__in=ids_to_delete).delete()
                    deleted_total += len(ids_to_delete)
                    pbar.update(len(ids_to_delete))

            print(f"Deleted {deleted_total} collections")
        else:
            print("No collections to delete")

    def _bulk_create_collections(self, collections_batch: List[FavoriteCollection]) -> None:
        """Bulk create favorite collections"""
        transaction_context = transaction.atomic() if self.use_transaction_per_batch else nullcontext()
        with transaction_context:
            FavoriteCollection.objects.bulk_create(
                collections_batch,
                batch_size=self.batch_size,
                ignore_conflicts=True
            )


class FavoriteItemsGenerator:
    """Generate favorite items for specified users"""

    def __init__(self, batch_size: int = 10000, use_transaction_per_batch: bool = False):
        self.batch_size = batch_size
        self.use_transaction_per_batch = use_transaction_per_batch

    def generate_for_users(
            self,
            user_ids: List[int],
            min_items: int = 10,
            max_items: int = 50,
            user_batch_size: int = 500
    ) -> None:
        if not user_ids:
            print("No user IDs provided")
            return

        all_products = list(Product.objects.values_list('id', flat=True))
        if not all_products:
            print("No products found to add to favorites")
            return

        print(f"Processing {len(user_ids)} users for favorites generation")
        print(f"Items per collection: {min_items}-{max_items}")
        print(f"Total products available: {len(all_products)}")

        total_collections_processed = 0
        favorite_items_batch = []
        batch_count = 0
        total_items_created = 0

        progress_bar = tqdm(
            range(0, len(user_ids), user_batch_size),
            desc="Processing user batches",
            unit="batches"
        )

        for start_idx in progress_bar:
            end_idx = min(start_idx + user_batch_size, len(user_ids))
            current_user_ids = user_ids[start_idx:end_idx]

            collections = list(FavoriteCollection.objects.filter(
                user_id__in=current_user_ids,
                is_default=True
            ).values_list('id', 'user_id'))

            if not collections:
                continue

            total_collections_processed += len(collections)

            for collection_id, user_id in collections:
                items_count = random.randint(min_items, max_items)
                selected_products = random.sample(all_products, min(items_count, len(all_products)))

                for position, product_id in enumerate(selected_products, start=1):
                    favorite_item = self._create_favorite_item(
                        collection_id=collection_id,
                        product_id=product_id,
                        position=position
                    )
                    favorite_items_batch.append(favorite_item)
                    total_items_created += 1

                    if len(favorite_items_batch) >= self.batch_size:
                        self._bulk_create_favorite_items(favorite_items_batch)
                        batch_count += 1
                        progress_bar.set_postfix(
                            collections=total_collections_processed,
                            batches=batch_count,
                            items=total_items_created
                        )
                        favorite_items_batch = []

        if favorite_items_batch:
            self._bulk_create_favorite_items(favorite_items_batch)
            batch_count += 1

        print(
            f"Generated {total_items_created} favorite items for {total_collections_processed}"
            f" collections in {batch_count} batches")

    @staticmethod
    def clear_all_items_except_admin() -> None:
        print("Clearing all favorite items except admin user...")

        items_to_delete = FavoriteItem.objects.exclude(collection__user__username='admin')
        count = items_to_delete.count()

        if count > 0:
            with tqdm(total=count, desc="Deleting favorite items", unit="items") as pbar:
                batch_size = 10000
                deleted_total = 0

                while True:
                    ids_to_delete = list(items_to_delete.values_list('id', flat=True)[:batch_size])
                    if not ids_to_delete:
                        break

                    FavoriteItem.objects.filter(id__in=ids_to_delete).delete()
                    deleted_total += len(ids_to_delete)
                    pbar.update(len(ids_to_delete))

            print(f"Deleted {deleted_total} favorite items")
        else:
            print("No favorite items to delete")

    @staticmethod
    def _create_favorite_item(collection_id: int, product_id: int, position: int) -> FavoriteItem:
        """Create a single favorite item"""

        note = ""
        if random.random() < 0.1:
            notes = [
                "Love this item!",
                "Want to buy later",
                "Great quality",
                "Perfect for summer",
                "Gift idea",
                "Waiting for sale",
                "Favorite color",
                "Must have",
            ]
            note = random.choice(notes)

        return FavoriteItem(
            collection_id=collection_id,
            product_id=product_id,
            position=position,
            note=note,
        )

    def _bulk_create_favorite_items(self, favorite_items_batch: List[FavoriteItem]) -> None:
        """Bulk create favorite items"""
        transaction_context = transaction.atomic() if self.use_transaction_per_batch else nullcontext()
        with transaction_context:
            FavoriteItem.objects.bulk_create(
                favorite_items_batch,
                batch_size=self.batch_size,
                ignore_conflicts=True
            )
