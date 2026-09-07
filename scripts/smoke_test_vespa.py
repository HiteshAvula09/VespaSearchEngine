import json
import urllib.parse
import urllib.request

BASE = "http://localhost:8080"
DOC_ID = "manual-smoke-test"

payload = {
    "fields": {
        "doc_id": DOC_ID,
        "parent_id": "manual",
        "chunk_id": "manual:0",
        "source": "github",
        "source_type": "test",
        "title": "Authentication migration",
        "content": "The engineering team selected OAuth2 for the authentication migration.",
        "author": "demo",
        "url": "https://example.com",
        "updated_at": 0,
        "metadata_json": "{}"
    }
}

request = urllib.request.Request(
    f"{BASE}/document/v1/vespasearch/enterprise/docid/{DOC_ID}",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(request, timeout=90) as response:
    print("Feed:", response.read().decode())

params = {
    "yql": "select * from enterprise where default contains text(@user-query)",
    "user-query": "authentication OAuth2",
    "ranking": "bm25",
    "hits": "5"
}

url = f"{BASE}/search/?" + urllib.parse.urlencode(params)

with urllib.request.urlopen(url, timeout=30) as response:
    print(json.dumps(json.loads(response.read().decode()), indent=2))
