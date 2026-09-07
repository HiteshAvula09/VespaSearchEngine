import argparse
import csv
import json
import time
from pathlib import Path
from vespasearch.vespa_client import VespaClient

MODES = ("bm25", "semantic", "hybrid")

def choose_key(hit):
    return str(hit.get("doc_id") or hit.get("parent_id") or hit.get("id") or "")

def clean_preview(text, limit=350):
    text = " ".join((text or "").split())
    return text[:limit] + ("..." if len(text) > limit else "")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", default="../evaluation/queries.json")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--results", default="../evaluation/retrieved_results.csv")
    parser.add_argument("--judging", default="../evaluation/judging.csv")
    args = parser.parse_args()

    items = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    client = VespaClient()

    result_rows = []
    pooled = {}

    for i, item in enumerate(items, start=1):
        qid = item["id"]
        query = item["query"]
        source = item.get("source")
        print(f"[{i}/{len(items)}] {qid}: {query}")

        for mode in MODES:
            start = time.perf_counter()
            hits = client.search(query=query, mode=mode, source=source, hits=args.k)
            latency_ms = (time.perf_counter() - start) * 1000

            for rank, hit in enumerate(hits, start=1):
                key = choose_key(hit)
                row = {
                    "query_id": qid,
                    "query": query,
                    "source_filter": source or "all",
                    "mode": mode,
                    "rank": rank,
                    "result_key": key,
                    "doc_id": hit.get("doc_id", ""),
                    "parent_id": hit.get("parent_id", ""),
                    "source": hit.get("source", ""),
                    "title": hit.get("title", ""),
                    "content_preview": clean_preview(hit.get("content", "")),
                    "relevance_score": hit.get("relevance", ""),
                    "query_latency_ms": round(latency_ms, 2),
                }
                result_rows.append(row)

                pool_key = (qid, key)
                if pool_key not in pooled:
                    pooled[pool_key] = {
                        "query_id": qid,
                        "query": query,
                        "source_filter": source or "all",
                        "result_key": key,
                        "doc_id": hit.get("doc_id", ""),
                        "parent_id": hit.get("parent_id", ""),
                        "source": hit.get("source", ""),
                        "title": hit.get("title", ""),
                        "content_preview": clean_preview(hit.get("content", "")),
                        "seen_in_modes": {mode},
                        "best_rank": rank,
                        "relevant": "",
                    }
                else:
                    pooled[pool_key]["seen_in_modes"].add(mode)
                    pooled[pool_key]["best_rank"] = min(pooled[pool_key]["best_rank"], rank)

    results_path = Path(args.results)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result_rows[0].keys()))
        writer.writeheader()
        writer.writerows(result_rows)

    judging_rows = []
    for item in pooled.values():
        item = dict(item)
        item["seen_in_modes"] = ",".join(sorted(item["seen_in_modes"]))
        judging_rows.append(item)

    judging_rows.sort(key=lambda r: (r["query_id"], r["best_rank"], r["title"]))

    judging_path = Path(args.judging)
    with judging_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(judging_rows[0].keys()))
        writer.writeheader()
        writer.writerows(judging_rows)

    print()
    print(f"Created: {results_path}")
    print(f"Created: {judging_path}")
    print()
    print("NEXT:")
    print("Open judging.csv and fill ONLY the 'relevant' column:")
    print("  1 = relevant")
    print("  0 = not relevant")
    print("Do not change result_key or query_id.")

if __name__ == "__main__":
    main()
