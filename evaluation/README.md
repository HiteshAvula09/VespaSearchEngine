# VespaSearch Evaluation v2

This version uses manual relevance judgments.

## 1. Put this folder in your project root

```text
VespaSearch/
├── evaluation/
│   ├── queries.json
│   ├── prepare_judging.py
│   ├── score_judging.py
│   └── README.md
├── python/
├── frontend/
└── ...
```

## 2. Generate results to judge

From the `VespaSearch\python` directory:

```powershell
uv run python ..\evaluation\prepare_judging.py --k 5
```

This creates:

```text
evaluation\retrieved_results.csv
evaluation\judging.csv
```

## 3. Open judging.csv

Fill only the final `relevant` column:

```text
1 = relevant to the query
0 = not relevant
```

Judge the document based on the query, title, and content preview.

Do not change `query_id` or `result_key`.

A document can be relevant even if it is not the exact answer, as long as it genuinely helps answer the query.

## 4. Calculate final metrics

After every row has 1 or 0:

```powershell
uv run python ..\evaluation\score_judging.py --k 5
```

This creates:

```text
evaluation\final_metrics.csv
evaluation\final_query_metrics.csv
```

The final metrics are:

- Hit Rate@5
- Precision@5
- Recall@5
- MRR@5
- NDCG@5
- Average retrieval latency
- P50 retrieval latency

NDCG is correctly normalized between 0 and 1.

## Note about Recall

This demo uses pooled judgments: the relevant-document set is the union of unique Top-5 documents retrieved by BM25, Semantic, and Hybrid for each query.

That makes Recall@5 a recall measure relative to the judged candidate pool. This is appropriate for a small demo evaluation, but it is not a claim of exhaustive relevance across every document in the entire corpus.
