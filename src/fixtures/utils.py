from typing import List

from django.db import models, transaction, connection


def get_postgres_type(field: models.Field) -> str:
    if isinstance(field, (models.ForeignKey, models.IntegerField, models.PositiveIntegerField,
                          models.PositiveSmallIntegerField)):
        return 'integer'
    elif isinstance(field, models.BooleanField):
        return 'boolean'
    elif isinstance(field, models.DateTimeField):
        return 'timestamp with time zone'
    else:
        return 'text'


def copy_insert_data(model: type[models.Model], columns: List[str], data: List[tuple]):
    if not data:
        return

    table_name = model._meta.db_table
    temp_table_name = f"temp_copy_{table_name}"

    column_defs = []
    for col_name in columns:
        field = model._meta.get_field(col_name)
        pg_type = get_postgres_type(field)
        column_defs.append(f'"{col_name}" {pg_type}')

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
