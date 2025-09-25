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

    quote_name = connection.ops.quote_name

    fields = [model._meta.get_field(field_name) for field_name in columns]

    column_definitions = []
    for field in fields:
        postgres_type = get_postgres_type(field)
        column_definitions.append(f"{quote_name(field.column)} {postgres_type}")

    quoted_table_name = quote_name(table_name)
    quoted_temp_table_name = quote_name(temp_table_name)
    quoted_column_list = ", ".join(quote_name(field.column) for field in fields)

    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            f"CREATE TEMP TABLE {quoted_temp_table_name} ({', '.join(column_definitions)}) ON COMMIT DROP;"
        )

        sql_copy = f"COPY {quoted_temp_table_name} ({quoted_column_list}) FROM STDIN"
        with cursor.copy(sql_copy) as copy_context:
            for row in data:
                copy_context.write_row(row)

        cursor.execute(f"""
            INSERT INTO {quoted_table_name} ({quoted_column_list})
            SELECT {quoted_column_list} FROM {quoted_temp_table_name};
        """)


def get_approximate_table_count(model: type[models.Model]) -> int:
    if connection.vendor != "postgresql":
        return model.objects.count()

    table_name = model._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT reltuples::bigint FROM pg_class WHERE relname = %s",
            [table_name]
        )
        result = cursor.fetchone()
        return result[0] if result else 0


def analyze_table(model: type[models.Model]):
    if connection.vendor != "postgresql":
        return

    table_name = model._meta.db_table
    with connection.cursor() as cursor:
        original_autocommit = connection.get_autocommit()
        try:
            connection.set_autocommit(True)
            quoted_table_name = connection.schema_editor().quote_name(table_name)
            cursor.execute(f"ANALYZE {quoted_table_name};")
        finally:
            connection.set_autocommit(original_autocommit)
