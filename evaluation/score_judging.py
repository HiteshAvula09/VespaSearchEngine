import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

MODES = ("bm25", "semantic", "hybrid")

def dcg(binary_rels):
    return sum(rel / math.log2(rank + 1) for rank, rel in enumerate(binary_rels, start=1))

def ndcg_at_k(binary_rels, total_relevant, k):
    actual = dcg(binary_rels[:k])
    ideal_count = min(total_relevant, k)
    ideal = dcg([1] * ideal_count)
    return actual / ideal if ideal > 0 else 0.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="../evaluation/retrieved_results.csv")
    parser.add_argument("--judging", default="../evaluation/judging.csv")
    parser.add_argument("--output", default="../evaluation/final_metrics.csv")
    parser.add_argument("--details", default="../evaluation/final_query_metrics.csv")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    with open(args.judging, newline="", encoding="utf-8") as f:
        judging_rows = list(csv.DictReader(f))

    judgments = {}
    total_relevant_by_query = defaultdict(int)
    missing = []

    for row in judging_rows:
        value = (row.get("relevant") or "").strip()
        if value not in {"0", "1"}:
            missing.append((row["query_id"], row["title"]))
            continue
        rel = int(value)
        judgments[(row["query_id"], row["result_key"])] = rel
        if rel == 1:
            total_relevant_by_query[row["query_id"]] += 1

    if missing:
        print("ERROR: Some judgments are still blank or invalid.")
        print("Fill relevant with 1 or 0 for every row in judging.csv.")
        for qid, title in missing[:10]:
            print(f"  {qid}: {title}")
        raise SystemExit(1)

    with open(args.results, newline="", encoding="utf-8") as f:
        results = list(csv.DictReader(f))

    grouped = defaultdict(list)
    latency_by_qmode = {}

    for row in results:
        grouped[(row["query_id"], row["mode"])].append(row)
        latency_by_qmode[(row["query_id"], row["mode"])] = float(row["query_latency_ms"])

    detail_rows = []

    for (qid, mode), rows in grouped.items():
        rows.sort(key=lambda r: int(r["rank"]))
        topk = rows[:args.k]
        rels = [judgments.get((qid, r["result_key"]), 0) for r in topk]

        relevant_retrieved = sum(rels)
        total_relevant = total_relevant_by_query[qid]

        hit = 1.0 if relevant_retrieved > 0 else 0.0
        precision = relevant_retrieved / args.k
        recall = relevant_retrieved / total_relevant if total_relevant > 0 else 0.0

        rr = 0.0
        for rank, rel in enumerate(rels, start=1):
            if rel:
                rr = 1.0 / rank
                break

        ndcg = ndcg_at_k(rels, total_relevant, args.k)

        detail_rows.append({
            "query_id": qid,
            "mode": mode,
            f"hit_rate@{args.k}": round(hit, 4),
            f"precision@{args.k}": round(precision, 4),
            f"recall@{args.k}": round(recall, 4),
            f"mrr@{args.k}": round(rr, 4),
            f"ndcg@{args.k}": round(ndcg, 4),
            "relevant_retrieved": relevant_retrieved,
            "total_relevant_in_pool": total_relevant,
            "latency_ms": round(latency_by_qmode[(qid, mode)], 2),
        })

    details_path = Path(args.details)
    with details_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)

    summary_rows = []
    for mode in MODES:
        rows = [r for r in detail_rows if r["mode"] == mode]
        summary_rows.append({
            "mode": mode,
            f"avg_hit_rate@{args.k}": round(statistics.mean(r[f"hit_rate@{args.k}"] for r in rows), 4),
            f"avg_precision@{args.k}": round(statistics.mean(r[f"precision@{args.k}"] for r in rows), 4),
            f"avg_recall@{args.k}": round(statistics.mean(r[f"recall@{args.k}"] for r in rows), 4),
            f"avg_mrr@{args.k}": round(statistics.mean(r[f"mrr@{args.k}"] for r in rows), 4),
            f"avg_ndcg@{args.k}": round(statistics.mean(r[f"ndcg@{args.k}"] for r in rows), 4),
            "avg_latency_ms": round(statistics.mean(r["latency_ms"] for r in rows), 2),
            "p50_latency_ms": round(statistics.median(r["latency_ms"] for r in rows), 2),
        })

    output_path = Path(args.output)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print("=== FINAL METRICS ===")
    for r in summary_rows:
        print(
            f"{r['mode']:8s} "
            f"Hit@{args.k}={r[f'avg_hit_rate@{args.k}']:.3f}  "
            f"P@{args.k}={r[f'avg_precision@{args.k}']:.3f}  "
            f"R@{args.k}={r[f'avg_recall@{args.k}']:.3f}  "
            f"MRR@{args.k}={r[f'avg_mrr@{args.k}']:.3f}  "
            f"NDCG@{args.k}={r[f'avg_ndcg@{args.k}']:.3f}  "
            f"Latency={r['avg_latency_ms']:.1f} ms"
        )

    print()
    print(f"Saved summary: {output_path}")
    print(f"Saved per-query metrics: {details_path}")
    print("All NDCG values are normalized to the 0-1 range.")

if __name__ == "__main__":
    main()
