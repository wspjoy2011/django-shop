import time

from django.core.management.base import BaseCommand
from django.db import connection, DatabaseError
from django.apps import apps
from tqdm import tqdm


class Command(BaseCommand):
    help = "Rebuilds all indexes defined in models' Meta classes, creating only those that do not already exist."

    def _get_existing_indexes(self, cursor) -> set:
        cursor.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public';")
        return {row[0] for row in cursor.fetchall()}

    def handle(self, *args, **options):
        app_labels_to_scan = ['catalog', 'ratings', 'favorites', 'inventories', 'accounts']
        all_models = []
        for label in app_labels_to_scan:
            try:
                all_models.extend(apps.get_app_config(label).get_models())
            except LookupError:
                self.stdout.write(self.style.WARNING(f"App '{label}' not found, skipping."))

        if not all_models:
            self.stdout.write(self.style.ERROR("No models found. Nothing to do."))
            return

        self.stdout.write(self.style.NOTICE("Attempting to synchronize model indexes with the database..."))

        start_time = time.perf_counter()
        total_model_indexes = 0
        failed_count = 0

        with connection.cursor() as cursor:
            self.stdout.write("Checking current state of database indexes...")
            existing_indexes_before = self._get_existing_indexes(cursor)

            for model in tqdm(all_models, desc="Processing models"):
                if not getattr(model._meta, 'managed', False) or not getattr(model._meta, 'indexes', []):
                    continue

                table_name = model._meta.db_table
                total_model_indexes += len(model._meta.indexes)

                for index in model._meta.indexes:
                    index_name = index.name

                    columns_sql_parts = []
                    for field_name, order in index.fields_orders:
                        field = model._meta.get_field(field_name)
                        db_column_name = field.column
                        columns_sql_parts.append(f'"{db_column_name}" {order}')
                    columns_sql = ', '.join(columns_sql_parts)

                    sql = f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" ({columns_sql});'

                    try:
                        cursor.execute(sql)
                    except DatabaseError as e:
                        self.stdout.write(self.style.ERROR(f"\nFailed to execute command for index {index_name}: {e}"))
                        failed_count += 1

            self.stdout.write("Re-checking database indexes to count newly created ones...")
            existing_indexes_after = self._get_existing_indexes(cursor)

        newly_created_indexes = existing_indexes_after - existing_indexes_before

        duration = time.perf_counter() - start_time
        self.stdout.write(self.style.SUCCESS(f"\nIndex synchronization finished in {duration:.2f}s."))
        self.stdout.write(f"  - Total indexes defined in models: {total_model_indexes}")
        self.stdout.write(f"  - Indexes already existing in DB: {len(existing_indexes_before)}")
        self.stdout.write(self.style.SUCCESS(f"  - New indexes actually created: {len(newly_created_indexes)}"))

        if newly_created_indexes:
            self.stdout.write("    --- List of newly created indexes ---")
            for index_name in sorted(list(newly_created_indexes)):
                self.stdout.write(f"    - {index_name}")

        if failed_count:
            self.stdout.write(self.style.WARNING(f"  - Failed commands: {failed_count}"))
