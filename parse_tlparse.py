#!/usr/bin/env python3
import os
import re
import json
import argparse
from bs4 import BeautifulSoup

def parse_compilation_metrics_html(html_path):
    """
    Parse an HTML file with compilation metrics.
    Returns a dictionary with key metrics like compile time, restarts, etc.
    Adjust the parsing logic based on your file's structure.
    """
    metrics = {
        "compile_time": None,
        "backend_time": None,
        "restarts": 0,
        "failures": 0,
        "status": "unknown"
    }
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except Exception as e:
        print(f"Error reading {html_path}: {e}")
        return metrics

    # Example: Look for table rows with two cells (key, value).
    # You may need to adjust selectors based on your actual HTML.
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) == 2:
            key = cells[0].get_text(strip=True).lower()
            val = cells[1].get_text(strip=True)
            if "compile time" in key:
                metrics["compile_time"] = val
            elif "backend" in key:
                metrics["backend_time"] = val
            elif "restart" in key:
                try:
                    metrics["restarts"] = int(val)
                except ValueError:
                    metrics["restarts"] = val
            elif "failure" in key:
                try:
                    metrics["failures"] = int(val)
                except ValueError:
                    metrics["failures"] = val
            elif "status" in key:
                metrics["status"] = val
    return metrics

def parse_graph_break_file(txt_path):
    """
    Parse a text file containing a graph break reason.
    Returns the full content as a string.
    """
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return content
    except Exception as e:
        print(f"Error reading {txt_path}: {e}")
        return ""

def parse_recompile_reasons(json_path):
    """
    Parse a recompile_reasons JSON file.
    Returns a list of strings or parsed events.
    Assumes the file is a JSON array of strings.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Optionally, split each string by commas or further parse using regex.
        parsed = []
        for line in data:
            parts = [p.strip() for p in line.split(",")]
            event = {"label": parts[0], "details": parts[1:]}
            parsed.append(event)
        return parsed
    except Exception as e:
        print(f"Error reading {json_path}: {e}")
        return []

def aggregate_attempt_data(root_dir):
    """
    Walk the given directory recursively and aggregate data per compilation attempt.
    Returns a dictionary keyed by attempt id.
    """
    attempts = {}

    # Regex patterns for file types
    pattern_metrics = re.compile(r"compilation_metrics_(\d+)\.html")
    pattern_break = re.compile(r"dynamo_graph_break_reason_(\d+)\.txt")
    pattern_recompile = re.compile(r"recompile_reasons_(\d+)\.json")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            full_path = os.path.join(dirpath, fname)
            m_metrics = pattern_metrics.match(fname)
            m_break = pattern_break.match(fname)
            m_recompile = pattern_recompile.match(fname)

            if m_metrics:
                attempt_id = m_metrics.group(1)
                metrics = parse_compilation_metrics_html(full_path)
                attempts.setdefault(attempt_id, {})["compilation_metrics"] = metrics

            elif m_break:
                attempt_id = m_break.group(1)
                break_reason = parse_graph_break_file(full_path)
                # If multiple break files exist for one attempt, store as a list.
                attempts.setdefault(attempt_id, {}).setdefault("graph_breaks", []).append(break_reason)

            elif m_recompile:
                attempt_id = m_recompile.group(1)
                recompile_events = parse_recompile_reasons(full_path)
                attempts.setdefault(attempt_id, {})["recompile_reasons"] = recompile_events

    return attempts

def main():
    parser = argparse.ArgumentParser(description="Parse tlparse output logs and aggregate compilation metrics.")
    parser.add_argument("root_dir", help="Root directory containing tlparse output logs")
    parser.add_argument("-o", "--output", help="Output JSON file to write aggregated data", default="aggregated_compilation_data.json")
    args = parser.parse_args()

    aggregated_data = aggregate_attempt_data(args.root_dir)

    # For demonstration, pretty-print the aggregated data.
    print(json.dumps(aggregated_data, indent=2))

    # Optionally write to an output file.
    with open(args.output, "w", encoding="utf-8") as out_file:
        json.dump(aggregated_data, out_file, indent=2)
    print(f"Aggregated data written to {args.output}")

if __name__ == "__main__":
    main()