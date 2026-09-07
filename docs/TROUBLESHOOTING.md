# Troubleshooting

## Vespa

```powershell
docker compose ps
docker compose logs vespa --tail 200
curl.exe http://localhost:19071/state/v1/health
curl.exe http://localhost:8080/state/v1/health
```

Give Docker at least the memory required by Vespa's local tutorial (4 GB minimum).
More is recommended when also running Ollama.

## Inspect Neon

```powershell
cd python
uv run python -m vespasearch.inspect_neon --sample
```

If GitHub/Slack names differ from `.env`, update the table lists.

## Ollama

```powershell
docker compose exec ollama ollama list
docker compose exec ollama ollama pull qwen3:4b
```

You can temporarily set `LLM_ENABLED=false` to test retrieval without generation.

## CORS

Local frontend:
`CORS_ORIGINS=http://localhost:3000`

For Vercel, add your actual Vercel URL.
