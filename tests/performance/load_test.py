#!/usr/bin/env python3
"""Carga HTTP académica, sin dependencias, con umbrales reproducibles."""

import argparse
from collections import Counter
import http.client
import json
import math
import statistics
import ssl
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener, urlopen


class _DirectHTTPSConnection(http.client.HTTPSConnection):
    """Reach a fixed origin while retaining the URL host for TLS SNI/validation."""

    def __init__(self, host, *, connect_host, **kwargs):
        super().__init__(host, **kwargs)
        self.connect_host = connect_host

    def connect(self):
        raw_socket = socket.create_connection(
            (self.connect_host, self.port), self.timeout, self.source_address
        )
        try:
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self.host,
            )
        except Exception:
            raw_socket.close()
            raise


class _DirectHTTPSHandler(HTTPSHandler):
    """HTTPS transport that bypasses DNS/proxies without disabling TLS checks."""

    def __init__(self, connect_host):
        super().__init__(context=ssl.create_default_context())
        self.connect_host = connect_host

    def https_open(self, request):
        return self.do_open(
            _DirectHTTPSConnection,
            request,
            connect_host=self.connect_host,
            context=self._context,
        )


def build_opener_for_direct_https(url, connect_host):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("--connect-to requires a normal HTTPS URL without embedded credentials")
    if not connect_host or any(character.isspace() for character in connect_host):
        raise ValueError("--connect-to must be a hostname or IP address")
    return build_opener(ProxyHandler({}), _DirectHTTPSHandler(connect_host))


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def request_once(url, timeout, opener=None):
    started = time.perf_counter()
    status = 0
    error = None
    try:
        request = Request(url, headers={"Accept": "application/json"})
        response_context = (
            opener.open(request, timeout=timeout)
            if opener is not None
            else urlopen(request, timeout=timeout)
        )
        with response_context as response:
            response.read()
            status = response.status
    except HTTPError as exc:
        status = exc.code
        error = type(exc).__name__
    except (URLError, TimeoutError, OSError) as exc:
        error = type(exc).__name__
    return (time.perf_counter() - started) * 1000, status, error


def summarize_outcomes(results):
    """Expose HTTP and transport failure classes without storing response bodies."""
    status_counts = Counter(
        str(status) if status else "network_error" for _, status, _ in results
    )
    error_types = Counter(error for _, _, error in results if error is not None)
    return {
        "status_counts": dict(sorted(status_counts.items())),
        "error_types": dict(sorted(error_types.items())),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument(
        "--connect-to",
        help="Connect to this origin host while preserving the HTTPS URL host for Host/SNI/certificate validation.",
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--max-p95-ms", type=float, default=2000)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--output")
    args = parser.parse_args()

    opener = None
    if args.connect_to:
        try:
            opener = build_opener_for_direct_https(args.url, args.connect_to)
        except ValueError as error:
            parser.error(str(error))

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(request_once, args.url, args.timeout, opener)
            for _ in range(args.requests)
        ]
        results = [future.result() for future in as_completed(futures)]

    latencies = [row[0] for row in results]
    failures = [row for row in results if row[1] < 200 or row[1] >= 400]
    result = {
        "test_id": "PT-PERF-01",
        "url": args.url,
        "connect_to": args.connect_to,
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
    result.update(summarize_outcomes(results))
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
