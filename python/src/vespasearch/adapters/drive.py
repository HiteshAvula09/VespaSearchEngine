from typing import Iterable
from ..models import NormalizedDocument
from ..utils import first_value, as_text, stable_id, to_epoch_seconds, humanize_key


def normalize_drive(rows: Iterable[dict]) -> Iterable[NormalizedDocument]:
    for row in rows:
        parse_error = first_value(row, ["_ab_source_file_parse_error", "parse_error"])
        if parse_error not in (None, "", "null", "NULL"):
            continue

        content = as_text(first_value(row, ["content", "text", "body"]))
        if not content.strip():
            continue

        key = as_text(first_value(row, ["document_key", "id", "_ab_source_file_url"]))
        url = as_text(first_value(row, ["_ab_source_file_url", "url", "web_view_link"]))
        updated = first_value(row, ["_ab_source_file_last_modified", "modified_time", "updated_at"])

        yield NormalizedDocument(
            parent_id=f"drive:{stable_id(key, url)}",
            source="google_drive",
            source_type="document",
            title=humanize_key(key) or "Google Drive document",
            content=content,
            url=url,
            updated_at=to_epoch_seconds(updated),
            metadata={"document_key": key},
        )
