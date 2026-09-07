import argparse
import json
from .config import get_settings
from .vespa_client import VespaClient


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--mode", choices=["bm25", "semantic", "hybrid"], default=settings.default_search_mode)
    parser.add_argument("--source", choices=["slack", "google_drive", "github"], default=None)
    parser.add_argument("--hits", type=int, default=settings.top_k)
    args = parser.parse_args()

    results = VespaClient().search(args.query, args.mode, args.source, args.hits)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
