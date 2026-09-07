import argparse
import csv
import json
import math
import statistics
import time
from pathlib import Path

from vespasearch.vespa_client import VespaClient

MODES = ("bm25", "semantic", "hybrid")


def norm(value):
    return (value or "").strip().lower()


def hit_is_relevant(hit, item):
    relevant_ids = {str(x) for x in item.get("relevant_ids", []) if str(x).strip()}
    if relevant_ids:
        candidates = {
            str(hit.get("doc_id", "")),
            str(hit.get("parent_id", "")),
            str(hit.get("id", "")),
        }
        return bool(relevant_ids.intersection(candidates))

    title = norm(hit.get("title"))
    content = norm(hit.get("content"))

    title_terms = [norm(x) for x in item.get("relevant_title_contains", []) if norm(x)]
    content_terms = [norm(x) for x in item.get("relevant_content_contains", []) if norm(x)]

    title_match = any(term in title for term in title_terms) if title_terms else False
    content_match = all(term in content for term in content_terms) if content_terms else False

    return title_match or content_match


def count_known_relevant(item):
    ids = [x for x in item.get("relevant_ids", []) if str(x).strip()]
    if ids:
        return len(set(map(str, ids)))
    return 1


def dcg(rels):
    return sum(rel / math.log2(rank + 1) for rank, rel in enumerate(rels, start=1))


def ndcg_at_k(rels, total_relevant, k):
    rels = rels[:k]
    actual = dcg(rels)
    ideal_count = min(total_relevant, k)
    ideal = dcg([1] * ideal_count)
    return actual / ideal if ideal else 0.0


def metrics_for_query(results, item, k):
    results = results[:k]
    rels = [1 if hit_is_relevant(hit, item) else 0 for hit in results]

    relevant_retrieved = sum(rels)
    total_relevant = count_known_relevant(item)

    hit_rate = 1.0 if relevant_retrieved > 0 else 0.0
    precision = relevant_retrieved / k
    recall = min(relevant_retrieved / total_relevant, 1.0) if total_relevant else 0.0

    reciprocal_rank = 0.0
    for rank, rel in enumerate(rels, start=1):
        if rel:
            reciprocal_rank = 1.0 / rank
            break

    ndcg = ndcg_at_k(rels, total_relevant, k)

    return {
        "hit_rate": hit_rate,
        "precision": precision,
        "recall": recall,
        "mrr": reciprocal_rank,
        "ndcg": ndcg,
        "relevant_retrieved": relevant_retrieved,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate VespaSearch retrieval.")
    parser.add_argument("--queries", default="../evaluation/queries.json")
    parser.add_argument("--output", default="../evaluation/results.csv")
    parser.add_argument("--summary", default="../evaluation/summary.csv")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--ignore-source-filter", action="store_true")
    args = parser.parse_args()

    items = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    client = VespaClient()
    rows = []

    print(f"Loaded {len(items)} evaluation queries")
    print(f"Evaluating: {', '.join(MODES)}")
    print(f"K = {args.k}\n")

    for i, item in enumerate(items, start=1):
        query = item["query"]
        source = None if args.ignore_source_filter else item.get("source")
        print(f"[{i}/{len(items)}] {query}")

        for mode in MODES:
            start = time.perf_counter()
            results = client.search(query=query, mode=mode, source=source, hits=args.k)
            latency_ms = (time.perf_counter() - start) * 1000.0

            m = metrics_for_query(results, item, args.k)

            rows.append({
                "query_id": item.get("id", ""),
                "query": query,
                "source_filter": source or "all",
                "mode": mode,
                f"hit_rate@{args.k}": round(m["hit_rate"], 4),
                f"precision@{args.k}": round(m["precision"], 4),
                f"recall@{args.k}": round(m["recall"], 4),
                f"mrr@{args.k}": round(m["mrr"], 4),
                f"ndcg@{args.k}": round(m["ndcg"], 4),
                "relevant_retrieved": m["relevant_retrieved"],
                "latency_ms": round(latency_ms, 2),
                "top_1_title": results[0].get("title", "") if results else "",
                "top_1_doc_id": results[0].get("doc_id", "") if results else "",
                "top_1_parent_id": results[0].get("parent_id", "") if results else "",
            })

            print(
                f"  {mode:8s} Hit={m['hit_rate']:.0f} "
                f"P@{args.k}={m['precision']:.2f} "
                f"R@{args.k}={m['recall']:.2f} "
                f"MRR={m['mrr']:.2f} "
                f"NDCG={m['ndcg']:.2f} "
                f"{latency_ms:.1f} ms"
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = []
    for mode in MODES:
        mode_rows = [r for r in rows if r["mode"] == mode]
        summary_rows.append({
            "mode": mode,
            f"avg_hit_rate@{args.k}": round(statistics.mean(r[f"hit_rate@{args.k}"] for r in mode_rows), 4),
            f"avg_precision@{args.k}": round(statistics.mean(r[f"precision@{args.k}"] for r in mode_rows), 4),
            f"avg_recall@{args.k}": round(statistics.mean(r[f"recall@{args.k}"] for r in mode_rows), 4),
            f"avg_mrr@{args.k}": round(statistics.mean(r[f"mrr@{args.k}"] for r in mode_rows), 4),
            f"avg_ndcg@{args.k}": round(statistics.mean(r[f"ndcg@{args.k}"] for r in mode_rows), 4),
            "avg_latency_ms": round(statistics.mean(r["latency_ms"] for r in mode_rows), 2),
            "p50_latency_ms": round(statistics.median(r["latency_ms"] for r in mode_rows), 2),
        })

    summary_path = Path(args.summary)
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\n=== SUMMARY ===")
    for row in summary_rows:
        print(
            f"{row['mode']:8s} "
            f"Hit@{args.k}={row[f'avg_hit_rate@{args.k}']:.3f}  "
            f"P@{args.k}={row[f'avg_precision@{args.k}']:.3f}  "
            f"R@{args.k}={row[f'avg_recall@{args.k}']:.3f}  "
            f"MRR@{args.k}={row[f'avg_mrr@{args.k}']:.3f}  "
            f"NDCG@{args.k}={row[f'avg_ndcg@{args.k}']:.3f}  "
            f"Latency={row['avg_latency_ms']:.1f} ms"
        )

    print(f"\nDetailed results: {output_path}")
    print(f"Summary:          {summary_path}")
    print("\nIMPORTANT: For final/reportable metrics, replace starter substring labels")
    print("with manually verified relevant_ids in queries.json.")


if __name__ == "__main__":
    main()
