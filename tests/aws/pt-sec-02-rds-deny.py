#!/usr/bin/env python3
"""PT-SEC-02: una conexión TCP externa al endpoint privado debe fallar."""

import argparse
import json
import socket
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        with socket.create_connection((args.host, args.port), timeout=args.timeout):
            result = {
                "test_id": "PT-SEC-02",
                "passed": False,
                "reason": "conexion TCP externa aceptada",
            }
    except (TimeoutError, OSError) as exc:
        result = {
            "test_id": "PT-SEC-02",
            "passed": True,
            "reason": type(exc).__name__,
        }
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
