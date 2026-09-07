from pathlib import Path
import io
import sys
import time
import zipfile
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "vespa-app"
CONFIG_URL = "http://localhost:19071"
SEARCH_URL = "http://localhost:8080"


def wait_for(url: str, timeout: int = 180):
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
        time.sleep(3)

    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def application_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in APP.rglob("*"):
            if path.is_file() and path.name != "services.local-llm.example.xml":
                archive.write(path, path.relative_to(APP).as_posix())
    return buffer.getvalue()


def main():
    print("[1/3] Waiting for Vespa config server...")
    wait_for(f"{CONFIG_URL}/state/v1/health")

    print("[2/3] Deploying Vespa application package...")
    request = urllib.request.Request(
        f"{CONFIG_URL}/application/v2/tenant/default/prepareandactivate",
        data=application_zip(),
        headers={"Content-Type": "application/zip"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            print(response.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        raise

    print("[3/3] Waiting for Vespa query endpoint...")
    wait_for(f"{SEARCH_URL}/state/v1/health", 300)
    print("VespaSearch application deployed successfully.")


if __name__ == "__main__":
    main()
