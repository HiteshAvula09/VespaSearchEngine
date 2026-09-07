# Architecture

```text
Slack ─────────┐
Google Drive ──┼──> Airbyte Cloud ──> Neon PostgreSQL
GitHub ────────┘                           |
                                            v
                                     Python Processor
                              read -> clean -> normalize -> chunk
                                            |
                                            v
                                      Vespa Document API
                                            |
                    +-----------------------+-----------------------+
                    |                                               |
                    v                                               v
             Vespa BM25                                  Arctic Embed XS
                                                                |
                                                           384-D vector
                                                                |
                                                              HNSW
                    |                                               |
                    +-----------------------+-----------------------+
                                            |
                                      Hybrid Ranking
                                            |
                                           Top-K
                                            |
                                         FastAPI
                                            |
                                   Grounded RAG prompt
                                            |
                                   Local Qwen via Ollama
                                            |
                                Answer + source citations
                                            |
                                      Next.js UI
                                            |
                                         Vercel
```

Airbyte/Neon keep connector-specific tables separate. The Python processor is the
normalization boundary. Vespa receives one common search schema.

Google Drive currently arrives with parsed text in `google_drive.documents.content`,
so the baseline does not need PyMuPDF, python-docx or python-pptx.
