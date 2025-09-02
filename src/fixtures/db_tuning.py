from typing import List, Tuple, Dict

from django.db import connection
from django.db.utils import DatabaseError


def apply_postgresql_speed_settings() -> None:
    """Apply PostgreSQL settings for maximum bulk insert performance"""
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute("SET synchronous_commit = OFF;")

        cursor.execute("SET work_mem = '256MB';")

        cursor.execute("SET maintenance_work_mem = '512MB';")

        cursor.execute("SET session_replication_role = 'replica';")

        cursor.execute("SET checkpoint_segments = 32;") if connection.pg_version < 90500 else None

        cursor.execute("SET random_page_cost = 1.1;")


def restore_postgresql_settings() -> None:
    """Restore PostgreSQL settings to default"""
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute("SET synchronous_commit = ON;")
        cursor.execute("RESET work_mem;")
        cursor.execute("RESET maintenance_work_mem;")
        cursor.execute("SET session_replication_role = 'origin';")
        cursor.execute("RESET random_page_cost;")


def get_all_table_indexes(table_names: List[str]) -> Dict[str, List[Dict]]:
    """Get all non-unique indexes for specified tables"""
    if connection.vendor != "postgresql":
        return {}

    results = {}
    with connection.cursor() as cursor:
        for table_name in table_names:
            constraints = connection.introspection.get_constraints(cursor, table_name)
            indexes = []

            for name, meta in constraints.items():
                if (meta.get("index") and
                        not meta.get("unique") and
                        not meta.get("primary_key") and
                        not meta.get("foreign_key")):
                    indexes.append({
                        'name': name,
                        'columns': meta.get('columns', []),
                        'table': table_name
                    })

            results[table_name] = indexes

    return results


def drop_table_indexes(table_names: List[str]) -> Dict[str, bool]:
    """Drop all non-unique indexes from specified tables"""
    if connection.vendor != "postgresql":
        return {}

    results = {}
    indexes_info = get_all_table_indexes(table_names)

    with connection.cursor() as cursor:
        for table_name, indexes in indexes_info.items():
            for index_info in indexes:
                index_name = index_info['name']
                try:
                    cursor.execute(f'DROP INDEX IF EXISTS "{index_name}" CASCADE;')
                    results[index_name] = True
                except DatabaseError as e:
                    print(f"Failed to drop index {index_name}: {e}")
                    results[index_name] = False

    return results


def recreate_table_indexes(stored_indexes: Dict[str, List[Dict]]) -> Dict[str, bool]:
    """Recreate indexes from stored information"""
    if connection.vendor != "postgresql":
        return {}

    results = {}

    with connection.cursor() as cursor:
        for table_name, indexes in stored_indexes.items():
            for index_info in indexes:
                index_name = index_info['name']
                columns = index_info['columns']

                try:
                    columns_sql = ', '.join([f'"{col}"' for col in columns])
                    sql = f'CREATE INDEX "{index_name}" ON "{table_name}" ({columns_sql});'
                    cursor.execute(sql)
                    results[index_name] = True
                except DatabaseError as e:
                    print(f"Failed to recreate index {index_name}: {e}")
                    results[index_name] = False

    return results


def optimize_postgresql_for_bulk_operations(table_names: List[str]) -> Tuple[Dict[str, List[Dict]], Dict[str, bool]]:
    """
    Prepare PostgreSQL for bulk operations by:
    1. Applying performance settings
    2. Dropping non-unique indexes

    Returns (stored_indexes, drop_results) for later restoration
    """
    if connection.vendor != "postgresql":
        return {}, {}

    apply_postgresql_speed_settings()

    stored_indexes = get_all_table_indexes(table_names)

    drop_results = drop_table_indexes(table_names)

    return stored_indexes, drop_results


def restore_postgresql_after_bulk_operations(stored_indexes: Dict[str, List[Dict]]) -> Dict[str, bool]:
    """
    Restore PostgreSQL after bulk operations by:
    1. Recreating indexes
    2. Restoring settings
    3. Running ANALYZE to update statistics
    """
    if connection.vendor != "postgresql":
        return {}

    recreate_results = recreate_table_indexes(stored_indexes)

    restore_postgresql_settings()

    with connection.cursor() as cursor:
        for table_name in stored_indexes.keys():
            cursor.execute(f'ANALYZE "{table_name}";')

    return recreate_results
