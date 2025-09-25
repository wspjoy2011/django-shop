import random
from typing import List, Tuple

from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from tqdm import tqdm

from apps.catalog.models import Product
from apps.cart.models import Cart, CartItem
from fixtures.utils import copy_insert_data


class CartsGenerator:
    def __init__(
            self,
            user_fraction: float = 0.30,
            items_range: Tuple[int, int] = (1, 10),
            quantity_range: Tuple[int, int] = (1, 5),
            exclude_username: str = "admin",
            batch_size: int = 50000,
    ):
        self.user_fraction = user_fraction
        self.items_range = items_range
        self.quantity_range = quantity_range
        self.exclude_username = exclude_username
        self.batch_size = batch_size
        self.User = get_user_model()

    def generate(self):
        product_ids = list(Product.objects.values_list("id", flat=True))
        if not product_ids:
            return

        selected_user_ids = self._pick_users()
        if not selected_user_ids:
            return

        now = timezone.now()

        carts_rows = [(user_id, now, now) for user_id in selected_user_ids]
        copy_insert_data(
            Cart,
            ["user", "created_at", "updated_at"],
            carts_rows,
        )

        cart_map = dict(Cart.objects.filter(user_id__in=selected_user_ids).values_list("user_id", "id"))
        if not cart_map:
            return

        items_rows = []
        for user_id in tqdm(selected_user_ids, desc="Preparing carts with items"):
            cart_id = cart_map.get(user_id)
            if not cart_id:
                continue
            items_count = random.randint(self.items_range[0], self.items_range[1])
            used_products = set()

            for _ in range(items_count):
                product_id = random.choice(product_ids)
                while product_id in used_products:
                    product_id = random.choice(product_ids)
                used_products.add(product_id)
                quantity = random.randint(self.quantity_range[0], self.quantity_range[1])
                items_rows.append((cart_id, product_id, quantity, now, now))

        if items_rows:
            copy_insert_data(
                CartItem,
                ["cart", "product", "quantity", "created_at", "updated_at"],
                items_rows,
            )

    def _pick_users(self) -> List[int]:
        users_table = self.User._meta.db_table
        carts_table = Cart._meta.db_table
        picked: List[int] = []
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT u.id
                FROM {users_table} u
                LEFT JOIN {carts_table} c ON c.user_id = u.id
                WHERE u.username <> %s AND c.user_id IS NULL
                """,
                [self.exclude_username],
            )
            while True:
                rows = cursor.fetchmany(self.batch_size)
                if not rows:
                    break
                for (user_id,) in rows:
                    if random.random() <= self.user_fraction:
                        picked.append(user_id)
        return picked

    @staticmethod
    def clear_all(exclude_username: str = "admin") -> None:
        User = get_user_model()
        users_table = User._meta.db_table
        carts_table = Cart._meta.db_table
        items_table = CartItem._meta.db_table

        print(f"Clearing cart items for all users except '{exclude_username}'...")
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                DELETE FROM {items_table}
                WHERE cart_id IN (
                    SELECT c.id
                    FROM {carts_table} c
                    JOIN {users_table} u ON u.id = c.user_id
                    WHERE u.username <> %s
                )
                """,
                [exclude_username],
            )
            print(f"{cursor.rowcount} cart items deleted.")

        print(f"Clearing carts for all users except '{exclude_username}'...")
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                DELETE FROM {carts_table}
                WHERE user_id IN (
                    SELECT u.id
                    FROM {users_table} u
                    WHERE u.username <> %s
                )
                """,
                [exclude_username],
            )
            print(f"{cursor.rowcount} carts deleted.")
