import time
import os
import pickle
from pathlib import Path
from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway, generate_latest
from dynamo_explain_parser import DynamoExplainData

input_dir = Path("scripts/dynamo_explain_output")
output_dir = Path("scripts/metrics")
output_dir.mkdir(parents=True, exist_ok=True)

PUSHGATEWAY_URL = "http://pushgateway:9091"

# group and isolate metrics in its own registry
registry = CollectorRegistry()

break_reasons_counter = Counter(
    "break_reasons_counter",
    "Break reasons per model",
    ["model_family", "model_name", "reason"],
    registry=registry
)

graph_break_count_gauge = Gauge(
    "graph_break_count_total",
    "Total number of graph breaks per model",
    ["model_family", "model_name"],
    registry=registry
)

compile_time_gauge = Gauge(
    "compile_time_seconds",
    "Time taken to compile a model in seconds",
    ["model_family", "model_name"],
    registry=registry
)

def record(model_family, model_name, reason, log_file):
    # increment Prometheus counter
    break_reasons_counter.labels(model_family, model_name, reason).inc()

    # append to Loki log
    ts = int(time.time()*1e9)
    log_file.open("a").write(
        f"INFO: time={ts} model_family={model_family} model_name={model_name} reason=\"{reason}\"\n"
    )

def flush(job_name="compile_breaks", grouping_key=None):
    push_to_gateway(
        PUSHGATEWAY_URL,
        job=job_name,  # top-level name in Pushgateway
        grouping_key=grouping_key,  # job + grouping_key is the composite key
        registry=registry,
    )

# Scan the directory structure
for model_family_dir in input_dir.iterdir():
    if model_family_dir.is_dir():
        model_family = model_family_dir.name
        for pkl_file in model_family_dir.glob("*.pkl"):
            # Extract model name from filename
            try:
                model_name = pkl_file.stem.replace("_dynamo_explain", "")
            except ValueError:
                print(f"Skipping improperly named file: {pkl_file}")
                continue

            # Load the pickled DynamoExplainData
            with pkl_file.open("rb") as f:
                try:
                    data: DynamoExplainData = pickle.load(f)
                except Exception as e:
                    print(f"Failed to load {pkl_file}: {e}")
                    continue

            prom_file = output_dir / f"{model_family}_{model_name}_compile_breaks.prom"
            log_file = output_dir / f"{model_family}_{model_name}_compile_breaks.log"

            for break_reason in data.break_reasons:
                record(model_family, model_name, break_reason.reason, log_file)

            if data.compile_times:
                compile_time_gauge.labels(model_family, model_name).set(data.compile_times.total_time)

            graph_break_count_gauge.labels(model_family, model_name).set(data.graph_break_count)

            flush(grouping_key={"pipeline": os.getenv("BUILD_NUMBER")})

            with prom_file.open("w") as f:
                f.write(generate_latest().decode())
