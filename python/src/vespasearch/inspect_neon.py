import argparse
import json
from .config import get_settings
from .db import list_schemas, list_tables, list_columns, fetch_rows


def truncate(row: dict) -> dict:
    output = {}
    for key, value in row.items():
        if isinstance(value, str) and len(value) > 300:
            output[key] = value[:300] + "... [truncated]"
        else:
            output[key] = value
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    print("Schemas:", ", ".join(list_schemas()))

    for schema in [settings.slack_schema, settings.drive_schema, settings.github_schema]:
        print(f"\n[{schema}]")
        tables = list_tables(schema)

        if not tables:
            print("  (no tables)")
            continue

        for table in tables:
            print(f"  {table}: {', '.join(list_columns(schema, table))}")
            if args.sample:
                rows = fetch_rows(schema, table, 1)
                if rows:
                    print(json.dumps(truncate(rows[0]), indent=2, default=str))


if __name__ == "__main__":
    main()
