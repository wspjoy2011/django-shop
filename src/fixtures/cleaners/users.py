from django.contrib.auth import get_user_model
from django.db import transaction
from tqdm import tqdm

User = get_user_model()


class UserCleaner:

    def __init__(self):
        self._deletion_plan = [
            ("Users (except admin)", User.objects.exclude(username="admin")),
        ]

    def clean(self) -> None:
        with transaction.atomic():
            for label, qs in tqdm(self._deletion_plan, desc="Cleaning users"):
                deleted_count, _ = qs.delete()
                tqdm.write(f"Deleted {deleted_count} rows from {label}")
