# Airbyte + Neon

Expected destination namespaces:

- Slack -> `slack`
- Google Drive -> `google_drive`
- GitHub -> `github`

One Neon database is enough for the demo.

Google Drive currently uses:

`google_drive.documents`

with fields observed in the current setup:

- `content`
- `document_key`
- `_ab_source_file_url`
- `_ab_source_file_last_modified`
- `_ab_source_file_parse_error`

The processor skips Drive rows with a parse error.

Slack table names may include:

- `channel_messages`
- `threads`
- `channels`
- `users`
- `channel_members`

Only text-bearing messages/threads are indexed in the baseline.

GitHub stream/table names can vary. Run:

```powershell
cd python
uv run python -m vespasearch.inspect_neon
```

Then update `GITHUB_TABLES` in `.env`.
