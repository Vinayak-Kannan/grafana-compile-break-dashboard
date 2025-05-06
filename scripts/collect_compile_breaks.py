import time
import os
from pathlib import Path
# import torch
# import torch._dynamo as dynamo
# from transformers import AutoModel
# import numpy as np
# import umap
# from dynamo_explain_parser import DynamoExplainParser
from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway, generate_latest
from mock_dynamo_explain_data import load_mock_dynamo_explain_data

output_dir = Path("scripts/metrics")
output_dir.mkdir(parents=True, exist_ok=True)
PUSHGATEWAY_URL = "http://pushgateway:9091"

# group and isolate metrics in its own registry
registry = CollectorRegistry()

break_reasons_counter = Counter(
    "break_reasons_counter",
    "Break reasons per commit",
    ["model_family", "model_name", "model_commit", "reason"],
    registry=registry
)

graph_break_count_gauge = Gauge(
    "graph_break_count_total",
    "Total number of graph breaks per commit",
    ["model_family", "model_name", "model_commit"],
    registry=registry
)

compile_time_gauge = Gauge(
    "compile_time_seconds",
    "Time taken to compile a model in seconds",
    ["model_family", "model_name", "model_commit"],
    registry=registry
)

def record(model_family, model_name, model_commit, reason, log_file):
    # increment Prometheus counter
    break_reasons_counter.labels(model_family, model_name, model_commit, reason).inc()

    # append to Loki log
    ts = int(time.time()*1e9)
    log_file.open("a").write(
        f"time={ts} service_name=jenkins level=info model_family={model_family} model_name={model_name} model_commit={model_commit} reason=\"{reason}\"\n"
    )

def flush(job_name="compile_breaks", grouping_key=None):
    push_to_gateway(
        PUSHGATEWAY_URL,
        job=job_name,  # top-level name in Pushgateway
        grouping_key=grouping_key,  # job + grouping_key is the composite key
        registry=registry,
    )

# TODO: Pull models from config file
mock_dynamo_explain_data, mock_model_info = load_mock_dynamo_explain_data("scripts/templates/mock_dynamo_explain_data.json")

for data, model_info in zip(mock_dynamo_explain_data, mock_model_info):
    model_family = model_info.model_family
    model_name = model_info.model_name
    model_commit_hash = model_info.model_commit_hash

    prom_file = Path(f"scripts/metrics/{model_family}_{model_name}_{model_commit_hash}_compile_breaks.prom")
    log_file  = Path(f"scripts/metrics/{model_family}_{model_name}_{model_commit_hash}_compile_breaks.log")
    
    for break_reason in data.break_reasons:
        record(model_family, model_name, model_commit_hash, break_reason.reason, log_file)

    if data.compile_times:
        compile_time_gauge.labels(model_family, model_name, model_commit_hash).set(data.compile_times.total_time)

    graph_break_count_gauge.labels(model_family, model_name, model_commit_hash).set(data.graph_break_count)

    # push metrics to Prometheus Pushgateway
    flush(grouping_key={"pipeline": os.getenv("BUILD_NUMBER")})

    # also save metrics to prometheus file
    with prom_file.open("w") as f:
        f.write(generate_latest().decode())

    # # save dynamo.explain output to text file
    # with open("metrics/dynamo_explanation.txt", "w") as f:
    #     f.write(str(explanation))
