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
