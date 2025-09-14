import io
import os
import json
import pytest

# These files are created by setup scripts
SAMPLE_A = os.path.join("server", "uploads", "sample_a.txt")
SAMPLE_B = os.path.join("server", "uploads", "sample_b.txt")

@pytest.mark.integration
def test_verify_endpoint_min_similarity():
    # Ensure files exist
    assert os.path.exists(SAMPLE_A), f"Missing {SAMPLE_A}"
    assert os.path.exists(SAMPLE_B), f"Missing {SAMPLE_B}"

    # Optional: allow overriding base URL via env var
    base_url = os.environ.get("CHAKSHU_BASE_URL", "http://127.0.0.1:5000")
    url = f"{base_url}/verify?model=all-mpnet-base-v2"

    # Build multipart form
    import requests
    with open(SAMPLE_A, "rb") as fa, open(SAMPLE_B, "rb") as fb:
        files = [
            ("files", (os.path.basename(SAMPLE_A), fa, "text/plain")),
            ("files", (os.path.basename(SAMPLE_B), fb, "text/plain")),
        ]
        r = requests.post(url, files=files)
    assert r.status_code == 200, r.text

    data = r.json()
    assert data.get("count", 0) >= 1
    # Find the pair for our two files (order may vary because server renames files on upload)
    # We'll assert that at least one result has moderately high ngram OR paraphrase similarity.
    results = data.get("results", [])
    assert isinstance(results, list) and results, "No results returned"

    best = max(results, key=lambda x: max(x.get("ngram", 0), x.get("paraphrase", 0)))
    ngram = float(best.get("ngram", 0))
    para = float(best.get("paraphrase", 0))

    assert max(ngram, para) >= 0.25, f"Similarity too low: ngram={ngram}, paraphrase={para}"
