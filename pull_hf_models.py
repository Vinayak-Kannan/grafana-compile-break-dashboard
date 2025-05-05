#!/usr/bin/env python3
"""
pull_hf_models.py

Unified script to:
  - Print top-N Hugging Face models by downloads.
  - Perform a one-time scheduled scan (via SCHEDULED_SCAN env var) detecting new commits and running analysis.
  - Run in watch mode (--watch) to continuously poll for new commits.
  - Collect analysis outputs and metrics, record Prometheus counters, and save JSON for Grafana ingestion.

Usage:
  # One-time list
  python pull_hf_models.py [N]

  # Scheduled scan (e.g. via Jenkins with SCHEDULED_SCAN=1)
  SCHEDULED_SCAN=1 python pull_hf_models.py [N]

  # Continuous watch mode
  python pull_hf_models.py [N] --watch --interval SECONDS
"""

import sys
import os
import json
import time
import argparse
import dataclasses
from typing import List, Dict

# Try to import HF client; fallback HTTP if needed
try:
    from huggingface_hub import HfApi, ModelInfo
except ImportError:
    HfApi = None
import requests

# TorchDynamo & HF model loading
import torch
import torch._dynamo as dynamo
from transformers import AutoModel

# Parser and metrics
from dynamo_explain_parser import DynamoExplainParser, DynamoExplainData
from collect_compile_breaks import record, flush

# File paths
STATE_FILE = "last_model_commits.json"
OUTPUT_FILE = "analysis_results.json"


### Helper Functions ###

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


def analyze_model_raw(model_id: str) -> DynamoExplainData:
    """
    Load model, run Dynamo explain, parse with DynamoExplainParser, return structured data.
    """
    print(f"[*] Loading model {model_id}")
    model = AutoModel.from_pretrained(model_id)

    # Wrap forward to refine inputs (e.g., UMAP + seq-length hack)
    def forward_refined(**kwargs):
        input_ids = kwargs.get("input_ids")
        seq_len = input_ids.shape[1]
        mod_ids = input_ids.clone()
        mod_ids[0, 0] += seq_len
        arr = input_ids.cpu().numpy()
        reducer = umap.UMAP(n_neighbors=2, n_components=2, random_state=42)
        emb = reducer.fit_transform(arr)
        umap_val = torch.tensor(emb[0, 0], dtype=mod_ids.dtype, device=mod_ids.device)
        mod_ids[0, 0] += umap_val
        kwargs["input_ids"] = mod_ids
        return model.original_forward(**kwargs)

    model.original_forward = model.forward
    model.forward = forward_refined

    print(f"[*] Running TorchDynamo explain for {model_id}")
    inputs = {"input_ids": torch.ones(1, 10, dtype=torch.long)}
    explain_out = dynamo.explain(model.forward)(**inputs)

    data = DynamoExplainParser.parse_explain_output(explain_out)

    # Save raw explanation text
    out_txt = f"{model_id.replace('/', '_')}_dynamo_explanation.txt"
    with open(out_txt, 'w') as f:
        f.write(str(explain_out))
    print(f"[+] Saved raw explain output to {out_txt}")

    return data


def single_scan(n: int):
    """Print top-N models."""
    for i, mid in enumerate(fetch_top_models(n), start=1):
        print(f"{i:2d}. {mid}")


def scheduled_scan(n: int):
    """One-time scan: detect new commits, analyze, record metrics, save results."""
    last = load_state()
    new_state = {}
    results = {}
    for mid in fetch_top_models(n):
        sha = get_latest_commit(mid)
        new_state[mid] = sha
        if last.get(mid) != sha:
            print(f"[+] New commit for {mid}: {sha[:7]} – analyzing")
            data = analyze_model_raw(mid)
            for br in data.break_reasons:
                record(model=mid, commit=sha, reason=br.reason)
            flush(grouping_key={"model": mid, "commit": sha})
            results[mid] = dataclasses.asdict(data)
    save_state(new_state)
    if results:
        save_results(results)
    else:
        print("[*] No updates detected; no results to save.")


def watch_loop(n: int, interval: int):
    last = load_state()
    while True:
        new_state = {}
        results = {}
        for mid in fetch_top_models(n):
            sha = get_latest_commit(mid)
            new_state[mid] = sha
            if last.get(mid) != sha:
                print(f"[+] Detected new commit for {mid}: {sha[:7]} – analyzing")
                data = analyze_model_raw(mid)
                for br in data.break_reasons:
                    record(model=mid, commit=sha, reason=br.reason)
                flush(grouping_key={"model": mid, "commit": sha})
                results[mid] = dataclasses.asdict(data)
        save_state(new_state)
        if results:
            save_results(results)
        time.sleep(interval)
        last = new_state


### Main function to parse arguments and run the appropriate mode ###

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