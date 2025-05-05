#!/usr/bin/env python3
"""
pull_hf_models.py

Unified script to:
  - Print top-N Hugging Face models by downloads.
  - Perform a one-time scheduled scan (via env var) detecting new commits and running analysis.
  - Run in watch mode (via --watch) to continuously poll for new commits.

Usage:
  pip install huggingface_hub requests
  python pull_hf_models.py [N]
  SCHEDULED_SCAN=1 python pull_hf_models.py [N]
  python pull_hf_models.py [N] --watch --interval SECONDS
"""
import sys
import os
import json
import time
import argparse
from typing import List, Dict

# Try to import HF client; fallback HTTP if needed
try:
    from huggingface_hub import HfApi, ModelInfo
except ImportError:
    HfApi = None

import requests

# Import analysis function (ensure in PYTHONPATH or same dir)
from analyze_model import analyze_model

# State file for commit SHAs
STATE_FILE = "last_model_commits.json"


def load_state() -> Dict[str, str]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state: Dict[str, str]):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_top_models_hf_api(limit: int) -> List[ModelInfo]:
    api = HfApi()
    print(f"Fetching top {limit} models via huggingface_hub client…")
    return api.list_models(limit=limit, sort="downloads", direction=-1)


def fetch_top_models_http(limit: int) -> List[Dict]:
    url = "https://huggingface.co/api/models"
    params = {"sort": "downloads", "direction": -1, "limit": limit}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_latest_commit(model_id: str, api: 'HfApi') -> str:
    commits = api.list_repo_commits(model_id, limit=1)
    return commits[0].sha if commits else ""


def single_scan(n: int):
    if HfApi is not None:
        models = fetch_top_models_hf_api(n)
        for i, m in enumerate(models, start=1):
            print(f"{i:2d}. {m.modelId}  (downloads={m.downloads:,}, likes={m.likes:,})")
    else:
        models = fetch_top_models_http(n)
        for i, m in enumerate(models, start=1):
            print(f"{i:2d}. {m['id']}  (downloads={m.get('downloads','n/a')}, likes={m.get('likes','n/a')})")


def scheduled_scan(n: int):
    if HfApi is None:
        print("Error: huggingface_hub not installed. Cannot perform scheduled scan.")
        return
    api = HfApi()
    last_state = load_state()
    new_state: Dict[str, str] = {}
    models = fetch_top_models_hf_api(n)
    for m in models:
        mid = m.modelId
        sha = get_latest_commit(mid, api)
        new_state[mid] = sha
        if last_state.get(mid) != sha:
            print(f"[+] New commit for {mid}: {sha[:7]} – running analysis")
            analyze_model(mid)
    save_state(new_state)


def watch_loop(n: int, interval: int):
    if HfApi is None:
        print("Error: huggingface_hub not installed. Cannot watch models.")
        return
    api = HfApi()
    last_state = load_state()
    while True:
        new_state: Dict[str, str] = {}
        models = fetch_top_models_hf_api(n)
        for m in models:
            mid = m.modelId
            sha = get_latest_commit(mid, api)
            new_state[mid] = sha
            if last_state.get(mid) != sha:
                print(f"[+] Detected new commit for {mid}: {sha[:7]} – analyzing")
                analyze_model(mid)
        save_state(new_state)
        last_state = new_state
        print(f"Sleeping {interval}s before next check...")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Pull and monitor top Hugging Face models.")
    parser.add_argument('N', nargs='?', type=int, default=15,
                        help='Number of top models to fetch')
    parser.add_argument('--watch', action='store_true',
                        help='Continuously poll for new commits')
    parser.add_argument('--interval', type=int, default=3600,
                        help='Polling interval in seconds for watch mode')
    args = parser.parse_args()

    # Scheduled scan via env var
    if os.getenv('SCHEDULED_SCAN') == '1':
        scheduled_scan(args.N)
    # Watch mode
    elif args.watch:
        watch_loop(args.N, args.interval)
    # Default one-time listing
    else:
        single_scan(args.N)

if __name__ == '__main__':
    main()


'''

#!/usr/bin/env python3
"""
fetch_hf_models.py

Fetch the top-N models from the Hugging Face Hub, sorted by download count.
Later, you can extend this script to pull metadata (e.g., graph breaks or compilations)
and ship metrics into your Grafana pipeline.

Usage:
    pip install huggingface_hub requests
    python fetch_hf_models.py [N]
"""

import sys
from typing import List, Dict

try:
    from huggingface_hub import HfApi, ModelInfo
except ImportError:
    HfApi = None

import requests


def fetch_top_models_hf_api(limit: int = 15) -> List[ModelInfo]:
    """
    Use the official huggingface_hub client to fetch models.
    """
    api = HfApi()
    # sort by downloads descending
    return api.list_models(limit=limit, sort="downloads", direction=-1)


def fetch_top_models_http(limit: int = 15) -> List[Dict]:
    """
    Fallback: use the public REST API to fetch models.
    """
    url = "https://huggingface.co/api/models"
    params = {"sort": "downloads", "direction": -1, "limit": limit}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def main(n: int = 15):
    if HfApi is not None:
        print(f"Fetching top {n} models via huggingface_hub client…")
        models = fetch_top_models_hf_api(n)
        for i, m in enumerate(models, start=1):
            print(f"{i:2d}. {m.modelId}  (downloads={m.downloads:,}, likes={m.likes:,})")
    else:
        print("huggingface_hub not installed—falling back to HTTP API…")
        models = fetch_top_models_http(n)
        for i, m in enumerate(models, start=1):
            print(f"{i:2d}. {m['id']}  (downloads={m.get('downloads', 'n/a')}, likes={m.get('likes', 'n/a')})")

if __name__ == "__main__":
    try:
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    except ValueError:
        print("Usage: python fetch_hf_models.py [number_of_models]")
        sys.exit(1)
    main(count)

'''