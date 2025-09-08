import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker
from tqdm import tqdm

from fixtures.utils import copy_insert_data

User = get_user_model()
fake_generator = Faker()


class UserGenerator:

    def generate_users(
            self,
            total_count: int = 50000,
            email_domain: str = "example.com",
            raw_password: str = "password123",
    ) -> None:
        hashed_password = make_password(raw_password)
        current_time = timezone.now()

        names_pool_size = min(total_count, 10_000)
        print(f"Generating a pool of {names_pool_size:,} unique names...")
        names_pool = [
            (fake_generator.first_name(), fake_generator.last_name())
            for _ in range(names_pool_size)
        ]

        username_max_length = self._get_field_max_length(User.USERNAME_FIELD) or 150
        email_max_length = self._get_field_max_length("email") or 254

        users_data = []
        for i in tqdm(range(total_count), desc="Preparing user data"):
            unique_suffix = secrets.token_urlsafe(6)[:8]
            first_name, last_name = names_pool[i % names_pool_size]
            first_name_token = self._convert_to_ascii_token(first_name)
            last_name_token = self._convert_to_ascii_token(last_name)

            username = f"user_{unique_suffix}"[:username_max_length]
            email_local_part = f"{first_name_token}_{last_name_token}_{unique_suffix}"
            email = f"{email_local_part}@{email_domain}"[:email_max_length]

            users_data.append((
                username,
                first_name,
                last_name,
                email,
                hashed_password,
                False,
                True,
                False,
                current_time,
            ))

        print(f"Generated {len(users_data):,} users to be inserted.")

        columns = [
            'username', 'first_name', 'last_name', 'email', 'password',
            'is_staff', 'is_active', 'is_superuser', 'date_joined'
        ]

        copy_insert_data(User, columns, users_data)

        print("\n--- Sample of created users ---")
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
