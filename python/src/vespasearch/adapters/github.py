from typing import Iterable, Any

from ..models import NormalizedDocument
from ..utils import first_value, as_text, stable_id, to_epoch_seconds


def nested_value(value: Any, *keys: str) -> str:
    """
    Safely extract useful text from nested GitHub objects.

    Example:
        {"login": "hitesh"} -> "hitesh"
        {"full_name": "org/repo"} -> "org/repo"
    """
    if isinstance(value, dict):
        for key in keys:
            result = value.get(key)
            if result not in (None, ""):
                return as_text(result)

    return as_text(value)


def get_repository(row: dict) -> str:
    """
    Extract a readable GitHub repository name.
    """
    value = first_value(
        row,
        [
            "repository",
            "repo",
            "repository_name",
            "full_name",
        ],
    )

    if isinstance(value, dict):
        return nested_value(
            value,
            "full_name",
            "name",
            "html_url",
        )

    return as_text(value)


def get_author(row: dict) -> str:
    """
    Extract GitHub author/user login from nested or flat fields.
    """
    for field in [
        "user",
        "author",
        "creator",
        "committer",
    ]:
        value = row.get(field)

        if isinstance(value, dict):
            result = nested_value(
                value,
                "login",
                "name",
                "email",
            )

            if result:
                return result

        elif value not in (None, ""):
            return as_text(value)

    return as_text(row.get("login"))


def get_commit_message(row: dict) -> str:
    """
    Airbyte GitHub commits commonly store the actual commit
    message inside row["commit"]["message"].
    """
    commit = row.get("commit")

    if isinstance(commit, dict):
        message = commit.get("message")

        if message not in (None, ""):
            return as_text(message)

    return as_text(
        first_value(
            row,
            [
                "commit_message",
                "message",
            ],
        )
    )


def normalize_issue(row: dict) -> tuple[str, str]:
    title = as_text(row.get("title"))
    body = as_text(row.get("body"))

    content_parts = []

    if title.strip():
        content_parts.append(title.strip())

    if body.strip():
        content_parts.append(body.strip())

    return title, "\n\n".join(content_parts)


def normalize_comment(row: dict) -> tuple[str, str]:
    body = as_text(
        first_value(
            row,
            [
                "body",
                "comment_body",
                "text",
            ],
        )
    )

    issue_url = as_text(row.get("issue_url"))

    title = "GitHub comment"

    if issue_url:
        title = f"GitHub comment · {issue_url.rstrip('/').split('/')[-1]}"

    return title, body


def normalize_pull_request(row: dict) -> tuple[str, str]:
    title = as_text(row.get("title"))
    body = as_text(row.get("body"))

    parts = []

    if title.strip():
        parts.append(title.strip())

    if body.strip():
        parts.append(body.strip())

    return title or "GitHub pull request", "\n\n".join(parts)


def normalize_commit(row: dict) -> tuple[str, str]:
    message = get_commit_message(row)

    sha = as_text(row.get("sha"))

    title = (
        f"Commit {sha[:8]}"
        if sha
        else "GitHub commit"
    )

    return title, message


def normalize_repository(row: dict) -> tuple[str, str]:
    name = as_text(
        first_value(
            row,
            [
                "full_name",
                "name",
            ],
        )
    )

    description = as_text(row.get("description"))

    parts = []

    if name.strip():
        parts.append(name.strip())

    if description.strip():
        parts.append(description.strip())

    return name or "GitHub repository", "\n\n".join(parts)


def normalize_generic(row: dict, table_name: str) -> tuple[str, str]:
    """
    Fallback for GitHub tables we have not explicitly modeled yet.
    """
    title = as_text(
        first_value(
            row,
            [
                "title",
                "name",
                "subject",
                "full_name",
            ],
        )
    )

    body_parts = []

    for field in [
        "body",
        "text",
        "content",
        "message",
        "description",
        "review_body",
        "comment_body",
    ]:
        value = row.get(field)

        if value not in (None, ""):
            text = as_text(value).strip()

            if text:
                body_parts.append(text)

    content = "\n\n".join(
        dict.fromkeys(body_parts)
    )

    if not content and title:
        content = title

    return title or f"GitHub {table_name}", content


def normalize_github(
    rows: Iterable[dict],
    table_name: str,
) -> Iterable[NormalizedDocument]:

    table_lower = table_name.lower()

    for row in rows:

        # ---------------------------------------------------------
        # 1. Normalize content according to GitHub table
        # ---------------------------------------------------------
        if table_lower == "issues":
            title, content = normalize_issue(row)

        elif table_lower == "comments":
            title, content = normalize_comment(row)

        elif table_lower == "pull_requests":
            title, content = normalize_pull_request(row)

        elif table_lower == "commits":
            title, content = normalize_commit(row)

        elif table_lower == "repositories":
            title, content = normalize_repository(row)

        else:
            title, content = normalize_generic(
                row,
                table_name,
            )

        content = content.strip()

        if not content:
            continue

        # ---------------------------------------------------------
        # 2. Extract shared GitHub metadata
        # ---------------------------------------------------------
        source_id = first_value(
            row,
            [
                "id",
                "node_id",
                "number",
                "sha",
                "commit_sha",
                "html_url",
                "url",
            ],
            stable_id(
                table_name,
                title,
                content[:200],
            ),
        )

        repo = get_repository(row)

        author = get_author(row)

        url = as_text(
            first_value(
                row,
                [
                    "html_url",
                    "url",
                ],
            )
        )

        updated = first_value(
            row,
            [
                "updated_at",
                "created_at",
                "committed_at",
                "merged_at",
            ],
        )

        # ---------------------------------------------------------
        # 3. Human-readable title
        # ---------------------------------------------------------
        display_title = title

        if repo and repo not in display_title:
            display_title = (
                f"{display_title} · {repo}"
                if display_title
                else repo
            )

        # ---------------------------------------------------------
        # 4. Feed normalized GitHub document
        # ---------------------------------------------------------
        yield NormalizedDocument(
            parent_id=f"github:{stable_id(table_name, source_id)}",
            source="github",
            source_type=table_name,
            title=display_title or f"GitHub {table_name}",
            content=content,
            author=author,
            url=url,
            updated_at=to_epoch_seconds(updated),
            metadata={
                "table": table_name,
                "repository": repo,
                "source_id": as_text(source_id),
            },
        )