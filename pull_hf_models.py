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
OUTPUT_FILE = "analysis_results.json"


def load_state() -> Dict[str, str]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state: Dict[str, str]):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def save_results(results: Dict[str, dict]):
    """Write the collected analysis outputs to JSON for Grafana pipeline."""
    os.makedirs(os.path.dirname(OUTPUT_FILE) or '.', exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[+] Saved analysis results to {OUTPUT_FILE}")


def fetch_top_models(limit: int) -> List[str]:
    if HfApi:
        api = HfApi()
        infos = api.list_models(limit=limit, sort="downloads", direction=-1)
        return [m.modelId for m in infos]
    # HTTP fallback
    url = "https://huggingface.co/api/models"
    params = {"sort": "downloads", "direction": -1, "limit": limit}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return [m['id'] for m in resp.json()]


def get_latest_commit(model_id: str, api: 'HfApi') -> str:
    commits = api.list_repo_commits(model_id, limit=1)
    return commits[0].sha if commits else ""


def single_scan(n: int):
    """Print top-N models."""
    for i, mid in enumerate(fetch_top_models(n), start=1):
        print(f"{i:2d}. {mid}")


def scheduled_scan(n: int):
    """One-time scan: detect new commits, run analysis for updated models, save results."""
    if not HfApi:
        print("Error: huggingface_hub not installed. Cannot perform scheduled scan.")
        return
    api = HfApi()
    last = load_state()
    
    new_state: Dict[str, str] = {}
    results: Dict[str, dict] = {}

    for mid in fetch_top_models(n):
        sha = get_latest_commit(mid, api)
        new_state[mid] = sha
        if last.get(mid) != sha:
            print(f"[+] New commit for {mid}: {sha[:7]} – analyzing")
            metrics = analyze_model(mid)
            # Expect analyze_model to return a dict of metrics
            results[mid] = metrics

    save_state(new_state)
    if results:
        save_results(results)
    else:
        print("[*] No updates detected; no results to save.")


def watch_loop(n: int, interval: int):
    if not HfApi:
        print("Error: huggingface_hub not installed. Cannot watch models.")
        return
    api = HfApi()
    last_state = load_state()

    while True:
        new_state: Dict[str, str] = {}
        results: Dict[str, dict] = {}

        for mid in fetch_top_models(n):
            sha = get_latest_commit(mid, api)
            new_state[mid] = sha
            if last_state.get(mid) != sha:
                print(f"[+] Detected new commit for {mid}: {sha[:7]} – analyzing")
                metrics = analyze_model(mid)
                results[mid] = metrics

        save_state(new_state)
        if results:
            save_results(results)
        time.sleep(interval)
        last_state = new_state


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