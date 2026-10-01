#!/usr/bin/env python3
"""Carga HTTP académica, sin dependencias, con umbrales reproducibles."""

import argparse
import json
import math
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def request_once(url, timeout):
    started = time.perf_counter()
    status = 0
    error = None
    try:
        with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=timeout) as response:
            response.read()
            status = response.status
    except HTTPError as exc:
        status = exc.code
        error = type(exc).__name__
    except (URLError, TimeoutError, OSError) as exc:
        error = type(exc).__name__
    return (time.perf_counter() - started) * 1000, status, error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--max-p95-ms", type=float, default=2000)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--output")
    args = parser.parse_args()

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(request_once, args.url, args.timeout)
            for _ in range(args.requests)
        ]
        results = [future.result() for future in as_completed(futures)]

    latencies = [row[0] for row in results]
    failures = [row for row in results if row[1] < 200 or row[1] >= 400]
    result = {
        "test_id": "PT-PERF-01",
        "url": args.url,
        "requests": len(results),
        "concurrency": args.concurrency,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "latency_ms": {
            "min": round(min(latencies), 2),
            "mean": round(statistics.fmean(latencies), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2),
        },
        "errors": len(failures),
        "error_rate": round(len(failures) / len(results), 4),
        "thresholds": {
            "max_p95_ms": args.max_p95_ms,
            "max_error_rate": args.max_error_rate,
        },
    }
    result["passed"] = (
        result["latency_ms"]["p95"] <= args.max_p95_ms
        and result["error_rate"] <= args.max_error_rate
    )
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    print(payload)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
