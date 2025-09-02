import secrets
from contextlib import nullcontext

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker
from tqdm import tqdm

User = get_user_model()
fake_generator = Faker()


class UserGenerator:

    def __init__(self, batch_size: int = 5000, use_transaction_per_batch: bool = True):
        self.batch_size = batch_size
        self.use_transaction_per_batch = use_transaction_per_batch

    def generate_users(
            self,
            total_count: int = 50000,
            email_domain: str = "example.com",
            raw_password: str = "password123",
            ignore_conflicts: bool = False
    ) -> None:
        hashed_password = make_password(raw_password)
        current_time = timezone.now()

        names_pool_size = min(total_count, 10_000)
        names_pool = [
            (fake_generator.first_name(), fake_generator.last_name())
            for _ in range(names_pool_size)
        ]

        username_max_length = self._get_field_max_length(User.USERNAME_FIELD) or 150
        email_max_length = self._get_field_max_length("email") or 254

        total_created = 0

        for batch_start_index in tqdm(range(0, total_count, self.batch_size), desc="Bulk creating users"):
            current_batch_size = min(self.batch_size, total_count - batch_start_index)
            users_batch = []

            for user_index_in_batch in range(current_batch_size):
                unique_suffix = secrets.token_urlsafe(6)[:8]

                first_name, last_name = names_pool[(batch_start_index + user_index_in_batch) % names_pool_size]
                first_name_token = self._convert_to_ascii_token(first_name)
                last_name_token = self._convert_to_ascii_token(last_name)

                username = f"user_{unique_suffix}"[:username_max_length]

                email_local_part = f"{first_name_token}_{last_name_token}_{unique_suffix}"
                email = f"{email_local_part}@{email_domain}"[:email_max_length]

                users_batch.append(User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=hashed_password,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                    date_joined=current_time,
                ))

            transaction_context = transaction.atomic() if self.use_transaction_per_batch else nullcontext()

            with transaction_context:
                User.objects.bulk_create(
                    users_batch,
                    batch_size=self.batch_size,
                    ignore_conflicts=ignore_conflicts,
                )

            total_created += len(users_batch)


        sample_users = User.objects.order_by('-id')[:3]
        for user in sample_users:
            print(f"  - {user.username} | {user.email} | {user.first_name} {user.last_name}")

    @staticmethod
    def _get_field_max_length(field_name: str) -> int:
        field = User._meta.get_field(field_name)
        return getattr(field, 'max_length', None)

    @staticmethod
    def _convert_to_ascii_token(input_string: str) -> str:
        ascii_token = slugify(input_string, allow_unicode=False).replace("-", "_").lower()
        return ascii_token or "user"
