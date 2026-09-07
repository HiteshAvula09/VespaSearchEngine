from urllib.parse import quote
import time
import httpx
from .config import get_settings


class VespaClient:
    def __init__(self):
        self.settings = get_settings()
        self.base = self.settings.vespa_url.rstrip("/")

    def wait_until_ready(self, timeout_seconds: int = 180):
        deadline = time.time() + timeout_seconds
        last_error = None
        while time.time() < deadline:
            try:
                response = httpx.get(f"{self.base}/state/v1/health", timeout=5)
                if response.status_code == 200:
                    return
            except Exception as exc:
                last_error = exc
            time.sleep(3)
        raise RuntimeError(f"Vespa did not become ready: {last_error}")

    def put_document(self, doc_id: str, fields: dict):
        namespace = quote(self.settings.vespa_namespace, safe="")
        schema = quote(self.settings.vespa_schema, safe="")
        encoded_id = quote(doc_id, safe="")
        url = f"{self.base}/document/v1/{namespace}/{schema}/docid/{encoded_id}"
        response = httpx.post(url, json={"fields": fields}, timeout=90)
        response.raise_for_status()
        return response.json()

    def delete_all(self):
        namespace = quote(self.settings.vespa_namespace, safe="")
        schema = quote(self.settings.vespa_schema, safe="")
        cluster = quote(self.settings.vespa_content_cluster, safe="")
        url = (
            f"{self.base}/document/v1/{namespace}/{schema}/docid"
            f"?selection=true&cluster={cluster}"
        )
        response = httpx.delete(url, timeout=120)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, mode: str = "hybrid", source: str | None = None, hits: int = 5):
        if mode not in {"bm25", "semantic", "hybrid"}:
            raise ValueError("mode must be bm25, semantic or hybrid")

        source_filter = ""
        if source:
            if source not in {"slack", "google_drive", "github"}:
                raise ValueError("invalid source")
            source_filter = f' and source contains "{source}"'

        if mode == "bm25":
            yql = f"select * from enterprise where default contains text(@user-query){source_filter}"
            payload = {
                "yql": yql,
                "user-query": query,
                "ranking": "bm25",
                "hits": hits,
                "language": "en",
            }

        elif mode == "semantic":
            yql = (
                "select * from enterprise where "
                "{targetHits:50}nearestNeighbor(embedding,e)"
                f"{source_filter}"
            )
            payload = {
                "yql": yql,
                "user-query": query,
                "input.query(e)": "embed(arctic,@user-query)",
                "ranking": "semantic",
                "hits": hits,
                "language": "en",
            }

        else:
            lexical = "default contains ({targetHits:50}text(@user-query))"
            dense = "({targetHits:50}nearestNeighbor(embedding,e))"
            yql = f"select * from enterprise where ({lexical} or {dense}){source_filter}"
            payload = {
                "yql": yql,
                "user-query": query,
                "input.query(e)": "embed(arctic,@user-query)",
                "ranking": "hybrid",
                "hits": hits,
                "language": "en",
            }

        response = httpx.post(f"{self.base}/search/", json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        children = data.get("root", {}).get("children", []) or []

        results = []
        for hit in children:
            fields = hit.get("fields", {})
            results.append({
                "id": hit.get("id"),
                "relevance": hit.get("relevance"),
                "doc_id": fields.get("doc_id", ""),
                "parent_id": fields.get("parent_id", ""),
                "chunk_id": fields.get("chunk_id", ""),
                "source": fields.get("source", ""),
                "source_type": fields.get("source_type", ""),
                "title": fields.get("title", ""),
                "content": fields.get("content", ""),
                "author": fields.get("author", ""),
                "url": fields.get("url", ""),
                "updated_at": fields.get("updated_at", 0),
                "metadata_json": fields.get("metadata_json", "{}"),
                "matchfeatures": fields.get("matchfeatures", {}),
            })
        return results
