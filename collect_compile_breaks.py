# collect_compile_breaks.py  (snippet)
import time, json, prometheus_client, pathlib, sys, os

PROM_FILE = pathlib.Path("metrics/compile_breaks.prom")
LOG_FILE  = pathlib.Path("metrics/compile_breaks.log")
PROM_FILE.parent.mkdir(parents=True, exist_ok=True)

breaks_total = prometheus_client.Counter(
    "compile_breaks_total",
    "Torch.compile breaks per commit",
    ["model", "commit", "reason"]
)

def record(model, commit, reason):
    # 1. update Prometheus counter
    breaks_total.labels(model, commit, reason).inc()

    # 2. append log-fmt line for richer queries
    ts = int(time.time()*1e9)
    LOG_FILE.open("a").write(
        f"time={ts} model={model} commit={commit} reason=\"{reason}\"\n"
    )

# ...call `record()` for every failed commit...

# finally, dump current metrics snapshot
with PROM_FILE.open("w") as f:
    f.write(prometheus_client.generate_latest().decode())
