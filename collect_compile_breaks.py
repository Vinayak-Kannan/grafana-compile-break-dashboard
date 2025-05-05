# collect_compile_breaks.py  (snippet)
import time
import os
import pathlib
import torch
import torch._dynamo as dynamo
from transformers import AutoModel
import numpy as np
import umap
from dynamo_explain_parser import DynamoExplainParser
from prometheus_client import CollectorRegistry, Counter, push_to_gateway, generate_latest

PROM_FILE = pathlib.Path("metrics/compile_breaks.prom")
LOG_FILE  = pathlib.Path("metrics/compile_breaks.log")
PROM_FILE.parent.mkdir(parents=True, exist_ok=True)
PUSHGATEWAY_URL = "http://pushgateway:9091"

# group and isolate metrics in its own registry
registry = CollectorRegistry()

breaks_counter = Counter(
    "compile_breaks_total",
    "Torch.compile breaks per commit",
    ["model", "commit", "reason"],
    registry=registry
)

def record(model, commit, reason):
    # 1. update Prometheus counter
    breaks_counter.labels(model, commit, reason).inc()

    # 2. append log-fmt line for richer queries
    ts = int(time.time()*1e9)
    LOG_FILE.open("a").write(
        f"time={ts} model={model} commit={commit} reason=\"{reason}\"\n"
    )

def flush(job_name="compile_breaks", grouping_key=None):
    push_to_gateway(
        PUSHGATEWAY_URL,
        job=job_name,  # top-level name in Pushgateway
        grouping_key=grouping_key or {"model": model},  # job + grouping_key is the composite key
        registry=registry,
    )

# ...call `record()` for every failed commit...
model_name = "prajjwal1/bert-tiny"
model = AutoModel.from_pretrained(model_name)
inputs = {"input_ids": torch.ones(1, 10, dtype=torch.long)}


# Option 1: Modify your forward_refined function to accept keyword argumentsimport umap

def forward_refined(**kwargs):
    # Get the input_ids tensor
    input_ids = kwargs["input_ids"]
    
    # Get the second value in the shape (which is the sequence length)
    seq_length = input_ids.shape[1]
    
    # Create a copy of the input_ids to avoid modifying the original
    modified_input_ids = input_ids.clone()
    
    # Add the sequence length to the first element of input_ids
    # The first element is at position [0, 0]
    modified_input_ids[0, 0] += seq_length
    
    # Print for debugging
    print(f"Original first element: {input_ids[0, 0]}")
    print(f"Modified first element: {modified_input_ids[0, 0]}")
    print(f"Sequence length added: {seq_length}")
    
    # Apply UMAP transformation (arbitrary example)
    # Convert input_ids to a NumPy array for UMAP
    input_ids_np = input_ids.cpu().numpy()
    reducer = umap.UMAP(n_neighbors=2, n_components=2, random_state=42)
    umap_embedding = reducer.fit_transform(input_ids_np)

    # Print UMAP embedding for debugging
    print(f"UMAP embedding: {umap_embedding}")

    # Convert the UMAP embedding value to a PyTorch tensor
    umap_value = torch.tensor(umap_embedding[0, 0], dtype=modified_input_ids.dtype, device=modified_input_ids.device)

    # Add the UMAP value to the first element of modified_input_ids
    modified_input_ids[0, 0] += umap_value

    # Update the kwargs with the modified input_ids
    kwargs["input_ids"] = modified_input_ids
    
    # Call the original forward method with the modified inputs
    return model.original_forward(**kwargs)


# Not broken: tlparse logs/dedicated_log_torch_trace_v3ixwcdv.log -o tl_out/ --overwrite

# Save the original forward method
model.original_forward = model.forward
# Replace with your custom method
model.forward = forward_refined
# # Compile the model
# model = torch.compile(model)
# # Call the model
# model.forward(**inputs)

explanation = dynamo.explain(model.forward)(**inputs)
data = DynamoExplainParser.parse_explain_output(explanation)

for break_reason in data.break_reasons:
    record(model_name, 1, break_reason.reason)

flush(grouping_key={"pipeline": os.getenv("BUILD_NUMBER")})

# Save to a text file
with open("dynamo_explanation.txt", "w") as f:
    f.write(str(explanation))

# finally, dump current metrics snapshot
with PROM_FILE.open("w") as f:
    f.write(generate_latest().decode())

def main():
    """
    Example standalone invocation:
       python collect_compile_breaks.py
    """
    # (Re-run whatever recording logic you want here for manual runs)
    # For example, if you had a single-model demo, move that demo code here.
    pass
 
if __name__ == "__main__":
    main()
