import argparse
import json
from .config import get_settings
from .db import fetch_rows, list_tables
from .chunking import chunk_text
from .utils import stable_id
from .vespa_client import VespaClient
from .adapters.drive import normalize_drive
from .adapters.slack import normalize_slack
from .adapters.github import normalize_github


def normalized_documents(source: str):
    settings = get_settings()

    if source in ("all", "google_drive"):
        tables = set(list_tables(settings.drive_schema))
        if settings.drive_table in tables:
            yield from normalize_drive(fetch_rows(settings.drive_schema, settings.drive_table))
        else:
            print(f"[skip] {settings.drive_schema}.{settings.drive_table} not found")

    if source in ("all", "slack"):
        tables = set(list_tables(settings.slack_schema))
        for table in settings.slack_table_list:
            if table in tables:
                yield from normalize_slack(fetch_rows(settings.slack_schema, table), table)
            else:
                print(f"[skip] {settings.slack_schema}.{table} not found")

    if source in ("all", "github"):
        tables = set(list_tables(settings.github_schema))
        for table in settings.github_table_list:
            if table in tables:
                yield from normalize_github(fetch_rows(settings.github_schema, table), table)
            else:
                print(f"[skip] {settings.github_schema}.{table} not found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["all", "slack", "google_drive", "github"], default="all")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--limit-docs", type=int, default=0)
    args = parser.parse_args()

    settings = get_settings()
    client = VespaClient()
    client.wait_until_ready()

    if args.reset:
        print("[vespa] deleting indexed enterprise documents...")
        try:
            print(client.delete_all())
        except Exception as exc:
            print(f"[warning] reset returned: {exc}")

    doc_count = 0
    chunk_count = 0

    for doc in normalized_documents(args.source):
        if args.limit_docs and doc_count >= args.limit_docs:
            break

        chunks = chunk_text(doc.content, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            continue

        doc_count += 1

        for index, chunk in enumerate(chunks):
            chunk_id = f"{doc.parent_id}:chunk:{index}"
            document_id = stable_id(chunk_id)

            fields = {
                "doc_id": document_id,
                "parent_id": doc.parent_id,
                "chunk_id": chunk_id,
                "source": doc.source,
                "source_type": doc.source_type,
                "title": doc.title[:1000],
                "content": chunk,
                "author": doc.author[:500],
                "url": doc.url[:3000],
                "updated_at": int(doc.updated_at or 0),
                "metadata_json": json.dumps(doc.metadata, ensure_ascii=False, default=str),
            }

            client.put_document(document_id, fields)
            chunk_count += 1

            if chunk_count % 25 == 0:
                print(f"[feed] {chunk_count} chunks")

    print(f"[done] normalized documents={doc_count}; Vespa chunks={chunk_count}")


if __name__ == "__main__":
    main()
