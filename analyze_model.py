#!/usr/bin/env python3
"""
analyze_model.py

Defines a single function `analyze_model(model_id)` that:
  - Loads a specified Hugging Face model by ID
  - Wraps its forward() to modify inputs and integrate UMAP step
  - Runs TorchDynamo explain on the wrapped forward
  - Parses and visualizes the explanation
  - Saves the raw explanation to a file

Usage:
  from analyze_model import analyze_model
  analyze_model("prajjwal1/bert-tiny")
"""
import os
import torch
import torch._dynamo as dynamo
from transformers import AutoModel
import umap
from dynamo_explain_parser import DynamoExplainParser
from dynamo_explain_viewer import DynamoExplainViewer

# Default input template; adjust as needed
DEFAULT_INPUTS = {"input_ids": torch.ones(1, 10, dtype=torch.long)}


def analyze_model(model_id: str, inputs: dict = None, output_dir: str = None):
    """
    Load a model by `model_id`, perform a Dynamo explain run, and save/visualize the results.

    Args:
      model_id: Hugging Face model identifier (e.g. "bert-base-uncased").
      inputs: Dict of keyword args to pass into model.forward(); defaults to dummy input_ids.
      output_dir: Directory where explanation outputs (text files) are saved; current dir if None.
    """
    # Prepare inputs and output directory
    if inputs is None:
        inputs = DEFAULT_INPUTS
    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    # 1) Load model
    print(f"[*] Loading model {model_id}")
    model = AutoModel.from_pretrained(model_id)

    # 2) Define input-wrapping forward
    def forward_refined(**kwargs):
        # Example: add seq length to first token and incorporate a UMAP scalar
        input_ids = kwargs.get("input_ids")
        seq_len = input_ids.shape[1]
        mod_ids = input_ids.clone()
        mod_ids[0, 0] += seq_len
        # UMAP on CPU, trivial embedding
        arr = input_ids.cpu().numpy()
        reducer = umap.UMAP(n_neighbors=2, n_components=2, random_state=42)
        emb = reducer.fit_transform(arr)
        umap_val = torch.tensor(emb[0, 0], dtype=mod_ids.dtype, device=mod_ids.device)
        mod_ids[0, 0] += umap_val
        kwargs["input_ids"] = mod_ids
        return model.original_forward(**kwargs)

    # 3) Patch forward
    model.original_forward = model.forward
    model.forward = forward_refined

    # 4) Explain
    print(f"[*] Running TorchDynamo explain for {model_id}")
    explanation = dynamo.explain(model.forward)(**inputs)

    # 5) Parse and view
    data = DynamoExplainParser.parse_explain_output(explanation)
    DynamoExplainViewer.view_explain_output(data)

    # 6) Save raw explanation
    filename = os.path.join(output_dir, f"{model_id.replace('/', '_')}_dynamo_explanation.txt")
    with open(filename, "w") as f:
        f.write(str(explanation))
    print(f"[+] Saved explanation to {filename}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze a Hugging Face model with TorchDynamo explain.")
    parser.add_argument("model_id", type=str, help="Model identifier (e.g. praajwal1/bert-tiny)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Directory to save explanation files")
    args = parser.parse_args()
    analyze_model(args.model_id, output_dir=args.output_dir)
