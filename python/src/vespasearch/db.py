import json
from typing import Any
import psycopg
from psycopg.rows import dict_row
from .config import get_settings


def connect():
    return psycopg.connect(get_settings().database_url, row_factory=dict_row)


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def list_schemas() -> list[str]:
    sql = """
    SELECT schema_name
    FROM information_schema.schemata
    WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
    ORDER BY schema_name
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [r["schema_name"] for r in cur.fetchall()]


def list_tables(schema: str) -> list[str]:
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = %s AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (schema,))
        return [r["table_name"] for r in cur.fetchall()]


def list_columns(schema: str, table: str) -> list[str]:
    sql = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (schema, table))
        return [r["column_name"] for r in cur.fetchall()]


def fetch_rows(schema: str, table: str, limit: int | None = None) -> list[dict[str, Any]]:
    query = f"SELECT * FROM {quote_ident(schema)}.{quote_ident(table)}"
    params = ()
    if limit:
        query += " LIMIT %s"
        params = (limit,)
    with connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
