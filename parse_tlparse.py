"""
tl_parse.py

This script scans a specified directory (the tlparse output directory, e.g. "tl_out")
for files named compilation_metrics_*.html. It parses each file using BeautifulSoup to extract
the following simple metrics:
  - Compile Time
  - Backend Time
  - Restarts
  - Failures

It then aggregates the results into a dictionary (keyed by the numeric attempt id in the filename)
and writes the aggregated data to a JSON file.

Usage:
  python3 tl_parse.py <directory> [-o OUTPUT_JSON]

Example:
  python3 tl_parse.py tl_out -o aggregated_metrics.json
"""

#!/usr/bin/env python3
import os
import re
import json
import argparse
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

def parse_compilation_metrics(html_path):
    """
    Parse a compilation_metrics_*.html file to extract a few key metrics.

    Args:
      html_path (str): Path to the HTML file.
    
    Returns:
      dict: Dictionary with keys 'compile_time', 'backend_time', 'restarts', and 'failures'.
    """
    metrics = {
        "compile_time": None,
        "backend_time": None,
        "restarts": 0,
        "failures": 0,
    }

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except Exception as e:
        print(f"Error reading file {html_path}: {e}")
        return metrics

    # Look for table rows that have exactly two cells (assumed to be key-value pairs)
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) != 2:
            continue
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

    return metrics

def aggregate_metrics(directory):
    """
    Aggregate metrics from all compilation_metrics_*.html files in the given directory.

    Args:
      directory (str): Directory containing tlparse output HTML files.
    
    Returns:
      dict: Aggregated dictionary keyed by the attempt id (extracted from the filename).
    """
    aggregated = {}
    pattern = re.compile("compilation_metrics_(\\d+)\\.html")


    for dirpath, dirnames, filenames in os.walk(directory):
        for fname in filenames:
            match = pattern.match(fname)
            if match:
                attempt_id = match.group(1)
                file_path = os.path.join(dirpath, fname)
                metrics = parse_compilation_metrics(file_path)
                aggregated[attempt_id] = metrics
    return aggregated

def plot_compile_times(aggregated_data):
    """
    Plot a bar chart of compile times extracted from the aggregated data.
    
    Args:
      aggregated_data (dict): Dictionary keyed by attempt id with metrics data.
    """
    # Sort keys numerically
    attempt_ids = sorted(aggregated_data.keys(), key=lambda x: int(x))
    compile_times = []

    for attempt in attempt_ids:
        value = aggregated_data[attempt]["compile_time"]
        try:
            # Convert compile_time to float; if missing or not a number, default to 0.
            compile_time = float(value) if value is not None else 0.0
        except ValueError:
            compile_time = 0.0
        compile_times.append(compile_time)

    plt.figure(figsize=(10, 6))
    plt.bar(attempt_ids, compile_times, color="skyblue")
    plt.xlabel("Compilation Attempt ID")
    plt.ylabel("Compile Time (s)")
    plt.title("Compilation Times per Attempt")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def main():
    parser = argparse.ArgumentParser(
        description="Parse compilation_metrics_*.html files to extract simple graph recompilation metrics."
    )
    parser.add_argument("directory", help="Directory containing tlparse output HTML files (e.g., tl_out)")
    parser.add_argument("-o", "--output", help="Output JSON file for aggregated metrics", default="aggregated_metrics.json")
    args = parser.parse_args()
    
    aggregated_data = aggregate_metrics(args.directory)

    # Print the aggregated data for debugging.
    print("Aggregated Metrics:")
    for key, val in aggregated_data.items():
        print(f"Attempt {key}: {val}")
    
    # Plot compile times from the aggregated data.
    plot_compile_times(aggregated_data)

    """
    # Optionally, write the aggregated data to a JSON file.

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(aggregated_data, f, indent=2)
    
    print(f"Aggregated metrics saved to {args.output}")
    """
    

if __name__ == "__main__":
    main()

'''
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

'''