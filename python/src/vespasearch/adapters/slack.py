from typing import Iterable
from ..models import NormalizedDocument
from ..utils import first_value, as_text, stable_id, to_epoch_seconds


def normalize_slack(rows: Iterable[dict], table_name: str) -> Iterable[NormalizedDocument]:
    if not ("message" in table_name.lower() or "thread" in table_name.lower()):
        return

    for row in rows:
        content = as_text(first_value(row, ["text", "content", "message", "body"]))
        if not content.strip():
            continue

        channel = as_text(first_value(row, ["channel_name", "channel", "channel_id", "conversation"]))
        author = as_text(first_value(row, ["user_name", "username", "author", "user", "user_id"]))
        timestamp = first_value(row, ["ts", "timestamp", "created_at", "datetime"])
        thread_id = as_text(first_value(row, ["thread_ts", "thread_id"]))
        source_id = first_value(row, ["id", "client_msg_id", "ts", "timestamp"])
        url = as_text(first_value(row, ["permalink", "url"]))

        yield NormalizedDocument(
            parent_id=f"slack:{stable_id(table_name, source_id, thread_id)}",
            source="slack",
            source_type="thread" if "thread" in table_name.lower() else "message",
            title=f"Slack #{channel}" if channel else "Slack message",
            content=content,
            author=author,
            url=url,
            updated_at=to_epoch_seconds(timestamp),
            metadata={
                "table": table_name,
                "channel": channel,
                "thread_id": thread_id,
                "source_id": as_text(source_id),
            },
        )
