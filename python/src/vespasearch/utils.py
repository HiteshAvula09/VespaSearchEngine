import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


def first_value(row: dict[str, Any], names: list[str], default: Any = "") -> Any:
    lowered = {str(k).lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lowered:
            value = lowered[name.lower()]
            if value is not None and value != "":
                return value
    return default


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def stable_id(*parts: Any) -> str:
    raw = "|".join(as_text(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def to_epoch_seconds(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)):
        n = float(value)
        if n > 10_000_000_000:
            n /= 1000
        return int(n)

    text = str(value).strip()
    try:
        n = float(text)
        if n > 10_000_000_000:
            n /= 1000
        return int(n)
    except Exception:
        pass

    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return 0


def humanize_key(value: str) -> str:
    value = re.sub(r"\.[A-Za-z0-9]+$", "", value or "")
    value = re.sub(r"[_\-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()
