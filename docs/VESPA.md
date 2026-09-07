# Vespa design

The active embedding model is Snowflake `snowflake-arctic-embed-xs`, configured
through Vespa's Hugging Face Embedder.

The document embedding is generated inside Vespa from:

`title + content`

The field is a 384-dimensional `bfloat16` tensor using the `angular` distance
metric and an HNSW index.

Retrieval modes:

- BM25: lexical matching over title/content
- semantic: Vespa query embedding + nearestNeighbor
- hybrid: lexical `text()` OR nearestNeighbor, then a hybrid rank profile

The hybrid score uses normalized BM25 plus cosine similarity, following the
style demonstrated in Vespa's current hybrid-search tutorial.

The deployment helper uses the local Vespa Deploy API:
`POST /application/v2/tenant/default/prepareandactivate`

Therefore installing Vespa CLI is optional for this starter.
