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
import shutil

import inspect
import numpy as np
import umap

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
# from collect_compile_breaks import record, flush
from run_model_sample_code import get_model_sample_code
import ast

# File paths
STATE_FILE = "last_model_commits.json"
OUTPUT_FILE = "analysis_results.json"

model_family_dict = {
        k.lower().replace(' ', '-'): v
        for k, v in {
                "Audio-Text-to-Text": "Multimodal",
                "Image-Text-to-Text": "Multimodal",
                "Visual Question Answering": "Multimodal",
                "Document Question Answering": "Multimodal",
                "Video-Text-to-Text": "Multimodal",
                "Visual Document Retrieval": "Multimodal",
                "Any-to-Any": "Multimodal",
                "Depth Estimation": "Computer Vision",
                "Image Classification": "Computer Vision",
                "Object Detection": "Computer Vision",
                "Image Segmentation": "Computer Vision",
                "Text-to-Image": "Computer Vision",
                "Image-to-Text": "Computer Vision",
                "Image-to-Image": "Computer Vision",
                "Image-to-Video": "Computer Vision",
                "Unconditional Image Generation": "Computer Vision",
                "Video Classification": "Computer Vision",
                "Text-to-Video": "Computer Vision",
                "Zero-Shot Image Classification": "Computer Vision",
                "Mask Generation": "Computer Vision",
                "Zero-Shot Object Detection": "Computer Vision",
                "Text-to-3D": "Computer Vision",
                "Image-to-3D": "Computer Vision",
                "Image Feature Extraction": "Computer Vision",
                "Keypoint Detection": "Computer Vision",
                "Text Classification": "Natural Language Processing",
                "Token Classification": "Natural Language Processing",
                "Table Question Answering": "Natural Language Processing",
                "Question Answering": "Natural Language Processing",
                "Zero-Shot Classification": "Natural Language Processing",
                "Translation": "Natural Language Processing",
                "Summarization": "Natural Language Processing",
                "Feature Extraction": "Natural Language Processing",
                "Text Generation": "Natural Language Processing",
                "Text2Text Generation": "Natural Language Processing",
                "Fill-Mask": "Natural Language Processing",
                "Sentence Similarity": "Natural Language Processing",
                "Text Ranking": "Natural Language Processing",
                "Text-to-Speech": "Audio",
                "Text-to-Audio": "Audio",
                "Automatic Speech Recognition": "Audio",
                "Audio-to-Audio": "Audio",
                "Audio Classification": "Audio",
                "Voice Activity Detection": "Audio",
                "Tabular Classification": "Tabular",
                "Tabular Regression": "Tabular",
                "Time Series Forecasting": "Tabular",
                "Reinforcement Learning": "Reinforcement Learning",
                "Robotics": "Reinforcement Learning",
                "Graph Machine Learning": "Other"
        }.items()
}

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

def count_trainable_parameters(model):
    model_parameters = filter(lambda p: p.requires_grad, model.parameters())
    params = sum([np.prod(p.size()) for p in model_parameters])
    return params


def fetch_top_models(limit: int, model_family: str) -> List[str]:
        models = []
        model_infos = []
        # Build tasks list for the given model_family
        tasks = [task for task, family in model_family_dict.items() if family == model_family]
        if not tasks:
                print(f"[!] No tasks found for model_family '{model_family}'")
                return []
        else:
                print(f"[+] Tasks for model_family '{model_family}': {tasks}")

        if HfApi:
                api = HfApi()
                seen_ids = set()
                # Collect all models for each task
                for task in tasks:
                        try:
                                infos = api.list_models(limit=limit * 10, sort="downloads", direction=-1, pipeline_tag=task, expand=['safetensors'])
                                for m in infos:
                                        if m.id not in seen_ids:
                                                model_infos.append(m)
                                                seen_ids.add(m.id)
                        except Exception as e:
                                print(f"[!] Error fetching models for task '{task}': {e}")
                                continue
                # Sort all collected models by downloads (descending)
                # Filter out models where safetensors.parameters >= 1 billion
                def has_large_safetensors(m):
                        try:
                                params = m.safetensors.total
                                return params >= 1_000_000_000
                        except Exception:
                                return True

                print(len( model_infos), "models found")
                model_infos = [m for m in model_infos if not has_large_safetensors(m)]
                model_infos.sort(key=lambda m: getattr(m, "downloads", 0), reverse=True)
                count = 0
                for m in model_infos:
                        if count >= limit:
                                break
                        models.append(m.id)
                        count += 1
                return models
        print("Uh oh")
        return models


def get_latest_commit(model_id: str, api) -> str:
    commits = api.list_repo_commits(model_id)
    if not commits:
        return ""
    return commits[0].commit_id


def build_model_inputs(model):
    """
    Inspect model.forward signature and:
      - For text models (input_ids), patch forward to inject UMAP/seq-length hack,
        and return a dummy input_ids tensor.
      - For vision models (pixel_values), return a dummy image tensor.
    """
    sig = inspect.signature(model.forward)
    params = list(sig.parameters.keys())
    device = next(model.parameters()).device

    # TEXT MODELS
    if "input_ids" in params:
        # patch forward to refine inputs
        model.original_forward = model.forward

        def forward_refined(**kwargs):
            input_ids = kwargs["input_ids"]
            seq_len = input_ids.shape[1]
            mod_ids = input_ids.clone()
            mod_ids[0, 0] += seq_len

            arr = input_ids.cpu().numpy()
            reducer = umap.UMAP(n_neighbors=2, n_components=2, random_state=42)
            emb = reducer.fit_transform(arr)
            umap_val = torch.tensor(emb[0, 0],
                                   dtype=mod_ids.dtype,
                                   device=mod_ids.device)
            mod_ids[0, 0] += umap_val

            kwargs["input_ids"] = mod_ids
            return model.original_forward(**kwargs)

        model.forward = forward_refined
        # return a dummy batch of token indices
        return {"input_ids": torch.ones(1, 10, dtype=torch.long, device=device)}
    # VISION MODELS
    elif "pixel_values" in params:
        img_size = getattr(model.config, "image_size", 224)
        # no patching: just random image
        return {
            "pixel_values": torch.randn(1, 3, img_size, img_size,
                                        dtype=torch.float32,
                                        device=device)
        }
    else:
        raise RuntimeError(
            f"Cannot auto-build inputs for model; "
            f"forward signature keys: {params}"
        )
 

def analyze_model_raw(model_id: str) -> DynamoExplainData:
    """
    Load model, run Dynamo explain, parse with DynamoExplainParser, return structured data.
    """
    print(f"[*] Loading model {model_id}")
    model = AutoModel.from_pretrained(model_id)
    get_model_sample_code(model_id)

    # Dynamically build inputs and patch model.forward if needed
#     inputs = build_model_inputs(model)

    # Load inputs from the dictionary in text.txt
    # Load inputs from temp.txt as a Python dict with torch tensors
    with open('temp.txt', 'r') as f:
        content = f.read()
        # Use eval with restricted globals to allow torch.tensor and numpy arrays
        inputs = eval(content, {"torch": torch, "np": np, "numpy": np})
    # Convert lists to torch tensors if needed (in case eval parses as lists)
    for k, v in inputs.items():
        if not isinstance(v, torch.Tensor):
            inputs[k] = torch.tensor(v)

    print(f"[*] Running TorchDynamo explain for {model_id} with inputs {list(inputs)}")
    explain_out = dynamo.explain(model.forward)(**inputs)

    '''
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
    '''

    data = DynamoExplainParser.parse_explain_output(explain_out)   # Important for Grafana 

    '''
    # Save raw explanation text
    out_txt = f"{model_id.replace('/', '_')}_dynamo_explanation.txt"
    with open(out_txt, 'w') as f:
        f.write(str(explain_out))
    print(f"[+] Saved raw explain output to {out_txt}")
    '''

    return data


def single_scan(n: int):
    """Print top-N models."""
    for i, mid in enumerate(fetch_top_models(n, model_family='Multimodal'), start=1):
        print(f"{i:2d}. {mid}")


def scheduled_scan(n: int):
    """One-time scan: detect new commits, analyze, record metrics, save results."""
    api = HfApi()                  
    last = load_state()
    new_state = {}
    results = {}

    for mid in fetch_top_models(n):
        sha = get_latest_commit(mid, api)
        new_state[mid] = sha

        if last.get(mid) != sha:
            print(f"[+] New commit for {mid}: {sha[:7]} – analyzing")
            data = analyze_model_raw(mid)
            results[mid] = dataclasses.asdict(data)

    save_state(new_state)
    if results:
        save_results(results)
    else:
        print("[*] No updates detected; no results to save.")

'''
def scheduled_scan(n: int):
    """One-time scan: detect new commits, analyze, record metrics, save results."""
    last = load_state()
    new_state = {}
    results = {}
    for mid in fetch_top_models(n):
        sha = get_latest_commit(mid, HfApi)
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
'''


### Main function to parse arguments and run the appropriate mode ###

def main():
    parser = argparse.ArgumentParser(description="Pull and monitor top Hugging Face models.")
    parser.add_argument('N', nargs='?', type=int, default=3,
                        help='Number of top models to fetch')
    parser.add_argument('--watch', action='store_true',
                        help='Continuously poll for new commits')
    parser.add_argument('--interval', type=int, default=3600,
                        help='Polling interval in seconds for watch mode')
    args = parser.parse_args()

    # Scheduled scan via env var
    if False:
        scheduled_scan(args.N)
    # Default one-time listing
    else:
        single_scan(args.N)

if __name__ == '__main__':
    main()