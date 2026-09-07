# VespaSearch

**VespaSearch** is a full personal enterprise-search/RAG demo over Slack,
Google Drive and GitHub.

## Final stack

```text
Slack + Google Drive + GitHub
            |
            v
       Airbyte Cloud
            |
            v
       Neon PostgreSQL
            |
            v
      Python Processor
   clean + normalize + chunk
            |
            v
           Vespa
  BM25 + Arctic XS + HNSW
            |
            v
       Hybrid Search
            |
            v
         FastAPI
            |
            v
  Local Qwen 3 via Ollama
            |
            v
 Grounded answer + citations
            |
            v
      Next.js -> Vercel
```

## What you already have

The project assumes:

- Airbyte Cloud sources are configured.
- Neon is the Postgres destination.
- Slack -> Neon works.
- Google Drive -> Neon works.
- `google_drive.documents.content` contains extracted document text.
- GitHub will use the same Neon database under the `github` namespace.
- Docker Desktop is installed.

---

# STEP 1 - Extract

```powershell
cd C:\Users\YOUR_NAME\Documents\Projects
Expand-Archive .\VespaSearch.zip -DestinationPath .
cd .\VespaSearch
```

---

# STEP 2 - Configure Neon

Copy:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
```

Use a current/rotated Neon password. Never commit `.env`.

---

# STEP 3 - Create Python environment

From project root:

```powershell
cd python
uv sync
```

Inspect Neon:

```powershell
uv run python -m vespasearch.inspect_neon
```

More detailed:

```powershell
uv run python -m vespasearch.inspect_neon --sample
```

You want to see:

```text
slack
google_drive
github
```

If GitHub's actual Airbyte table names differ, edit `GITHUB_TABLES` in the root `.env`.

Return:

```powershell
cd ..
```

---

# STEP 4 - Start Vespa and Ollama

```powershell
docker compose up -d vespa ollama
docker compose ps
```

Check Vespa config server:

```powershell
curl.exe http://localhost:19071/state/v1/health
```

Wait until it reports `up`.

---

# STEP 5 - Deploy VespaSearch

You do not need Vespa CLI for this project.

```powershell
python .\scripts\deploy_vespa.py
```

This ZIPs `vespa-app` and deploys it through Vespa's local Deploy API.

The first deployment can take longer because the Arctic model must be downloaded.

Verify:

```powershell
curl.exe http://localhost:8080/state/v1/health
```

---

# STEP 6 - Smoke test Vespa

```powershell
python .\scripts\smoke_test_vespa.py
```

This feeds one manual document and searches it using BM25.

At this point you have independently proved:

```text
Docker -> Vespa -> application package -> Document API -> BM25 -> Query API
```

---

# STEP 7 - Pull local LLM

```powershell
docker compose exec ollama ollama pull qwen3:4b
docker compose exec ollama ollama list
```

This is free local inference.

---

# STEP 8 - Test Neon -> Python -> Vespa

```powershell
cd python
```

Start with two Drive records:

```powershell
uv run python -m vespasearch.ingest --source google_drive --limit-docs 2
```

Search:

```powershell
uv run python -m vespasearch.search_cli "What is Project Orion?" --mode hybrid
```

If good, feed all Drive:

```powershell
uv run python -m vespasearch.ingest --source google_drive
```

Slack:

```powershell
uv run python -m vespasearch.ingest --source slack
```

GitHub:

```powershell
uv run python -m vespasearch.ingest --source github
```

Or rebuild the whole Vespa index:

```powershell
uv run python -m vespasearch.ingest --source all --reset
```

Important: Vespa creates the embeddings. Python does not call an external
embedding API.

---

# STEP 9 - Compare Vespa search modes

BM25:

```powershell
uv run python -m vespasearch.search_cli "authentication OAuth2" --mode bm25
```

Semantic:

```powershell
uv run python -m vespasearch.search_cli "how are users authenticated" --mode semantic
```

Hybrid:

```powershell
uv run python -m vespasearch.search_cli "how are users authenticated" --mode hybrid
```

Google Drive only:

```powershell
uv run python -m vespasearch.search_cli "Project Orion" --mode hybrid --source google_drive
```

---

# STEP 10 - Start FastAPI

Stay in `python`:

```powershell
uv run uvicorn vespasearch.api:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/docs
```

POST `/search` with:

```json
{
  "query": "What decisions were made about Project Orion?",
  "mode": "hybrid",
  "source": null,
  "hits": 5,
  "generate": true
}
```

Behind the scenes:

```text
Question
  |
  v
FastAPI
  |
  v
Vespa hybrid search
  |
  v
Top 5 chunks
  |
  v
Grounded prompt
  |
  v
Local Qwen
  |
  v
Answer + evidence
```

---

# STEP 11 - Start Next.js UI

Open another terminal:

```powershell
cd C:\path\to\VespaSearch\frontend
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

---

# STEP 12 - Vercel

The frontend is Vercel-ready.

For Vercel you need FastAPI on a public HTTPS URL (or a temporary HTTPS tunnel),
because the Vercel site cannot access your laptop's `localhost:8000`.

Set in Vercel:

```text
NEXT_PUBLIC_API_URL=https://YOUR-BACKEND
```

Update backend:

```text
CORS_ORIGINS=https://YOUR-VERCEL-SITE.vercel.app
```

See `docs/VERCEL.md`.

---

# What each component does

| Component | Job |
|---|---|
| Airbyte | sync connector data |
| Neon | store Airbyte output |
| Python | clean, normalize, chunk, feed |
| Vespa BM25 | lexical retrieval |
| Arctic XS | Vespa-integrated 384-D embedding |
| HNSW | approximate vector retrieval |
| Vespa rank profile | hybrid scoring |
| FastAPI | RAG orchestration/API |
| Ollama Qwen | free local grounded generation |
| Next.js | professional UI |
| Vercel | frontend hosting |

---

# Recommended build order

Do not start everything at once.

1. Verify Airbyte -> Neon.
2. Start Vespa.
3. Deploy Vespa app.
4. Run manual smoke test.
5. Feed 2 Drive docs.
6. Test hybrid search.
7. Feed all 3 connectors.
8. Add Ollama grounded answer.
9. Start FastAPI.
10. Start Next.js.
11. Deploy frontend last.

---

# Phase 2

After the baseline works:

- build a relevance evaluation set
- measure Recall@K, MRR, nDCG@K
- compare BM25 vs semantic vs hybrid
- tune rank profiles
- add an ONNX cross-encoder reranker if useful
- add ACL filtering if you make the demo multi-user
- optionally move generation into Vespa with LocalLLM + RAGSearcher

See `vespa-app/services.local-llm.example.xml`.
