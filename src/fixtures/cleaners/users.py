from django.contrib.auth import get_user_model
from django.db import connection
from tqdm import tqdm

User = get_user_model()


class UserCleaner:

    def clean(self) -> None:
        table_name = User._meta.db_table

        with connection.cursor() as cursor:
            tqdm.write(f"Executing fast delete on table: \"{table_name}\"")
            cursor.execute(f'DELETE FROM "{table_name}" WHERE is_superuser = FALSE;')
            tqdm.write(f"Deleted {cursor.rowcount:,} non-superuser rows.")
