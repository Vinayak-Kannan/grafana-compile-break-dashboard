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
    # increment Prometheus counter
    breaks_counter.labels(model, commit, reason).inc()

    # append to Loki log
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

# TODO: Pull models from config file
model_name = "prajjwal1/bert-tiny"
model = AutoModel.from_pretrained(model_name)
inputs = {"input_ids": torch.ones(1, 10, dtype=torch.long)}

def forward_refined(**kwargs):
    input_ids = kwargs["input_ids"]
    seq_length = input_ids.shape[1]
    modified_input_ids = input_ids.clone()
    modified_input_ids[0, 0] += seq_length
    
    # Apply UMAP transformation (arbitrary example)
    input_ids_np = input_ids.cpu().numpy()
    reducer = umap.UMAP(n_neighbors=2, n_components=2, random_state=42)
    umap_embedding = reducer.fit_transform(input_ids_np)

    umap_value = torch.tensor(umap_embedding[0, 0], dtype=modified_input_ids.dtype, device=modified_input_ids.device)
    modified_input_ids[0, 0] += umap_value
    kwargs["input_ids"] = modified_input_ids
    
    return model.original_forward(**kwargs)

model.original_forward = model.forward
model.forward = forward_refined

explanation = dynamo.explain(model.forward)(**inputs)
data = DynamoExplainParser.parse_explain_output(explanation)

for break_reason in data.break_reasons:
    record(model_name, 1, break_reason.reason)

# push metrics to Prometheus Pushgateway
flush(grouping_key={"pipeline": os.getenv("BUILD_NUMBER")})

# also save metrics to prometheus file
with PROM_FILE.open("w") as f:
    f.write(generate_latest().decode())

# save dynamo.explain output to text file
with open("metrics/dynamo_explanation.txt", "w") as f:
    f.write(str(explanation))
