#!/usr/bin/env python3
"""Private, secret-free readiness endpoint for a Tangamandapio VPN router."""
from __future__ import annotations

import argparse
import http.server
import ipaddress
import json
import logging
import re
import socket
import ssl
import subprocess
import sys


def is_ready(tailscale_state, wms_status):
    return tailscale_state == "Running" and wms_status == 200


def health_payload(tailscale_state, wms_status):
    return {
        "ready": is_ready(tailscale_state, wms_status),
        "tailscale": tailscale_state,
        "private_wms_http": wms_status,
    }


def read_tailscale_state():
    try:
        result = subprocess.run(["tailscale", "status", "--json"], capture_output=True,
                                text=True, timeout=1.0, check=True)
        state = json.loads(result.stdout).get("BackendState", "Unknown")
        return state if state in {"Running", "Starting", "NeedsLogin", "Stopped", "NoState"} else "Unknown"
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return "Unknown"


def probe_private_wms(private_ip, hostname, path="/api/health", timeout=1.5):
    address = ipaddress.ip_address(private_ip)
    if address.version != 4 or not address.is_private:
        raise ValueError("WMS destination must be a private IPv4 address")
    if not re.fullmatch(r"[a-z0-9-]+\.azurewebsites\.net", hostname):
        raise ValueError("invalid Function hostname")
    if not re.fullmatch(r"/[A-Za-z0-9_/-]*", path):
        raise ValueError("invalid health path")
    context = ssl.create_default_context()
    with socket.create_connection((str(address), 443), timeout=timeout) as raw:
        raw.settimeout(timeout)
        with context.wrap_socket(raw, server_hostname=hostname) as tls:
            tls.sendall((f"GET {path} HTTP/1.1\r\nHost: {hostname}\r\n"
                         "Connection: close\r\nUser-Agent: tangama-router-health/1\r\n\r\n").encode("ascii"))
            response_line = tls.makefile("rb").readline(4096).decode("ascii", errors="replace")
    parts = response_line.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return None
    return int(parts[1])


def check_components(private_ip, hostname):
    tailscale_state = read_tailscale_state()
    try:
        wms_status = probe_private_wms(private_ip, hostname)
    except (OSError, ssl.SSLError, TimeoutError, ValueError):
        wms_status = None
    return health_payload(tailscale_state, wms_status)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        result = check_components(self.server.wms_private_ip, self.server.wms_hostname)
        body = json.dumps(result, separators=(",", ":")).encode("utf-8")
        self.send_response(200 if result["ready"] else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        logging.info("router-health %s", format % args)


class HealthServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9797)
    parser.add_argument("--wms-private-ip", required=True)
    parser.add_argument("--wms-hostname", required=True)
    parser.add_argument("--check-once", action="store_true")
    args = parser.parse_args()
    try:
        ip = ipaddress.ip_address(args.wms_private_ip)
        if ip.version != 4 or not ip.is_private:
            raise ValueError("WMS IP must be private IPv4")
        if not 1 <= args.port <= 65535:
            raise ValueError("port is outside the valid range")
        if not re.fullmatch(r"[a-z0-9-]+\.azurewebsites\.net", args.wms_hostname):
            raise ValueError("invalid Function hostname")
        if args.check_once:
            result = check_components(str(ip), args.wms_hostname)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result["ready"] else 1
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        server = HealthServer((args.bind, args.port), Handler)
        server.wms_private_ip = str(ip)
        server.wms_hostname = args.wms_hostname
        server.serve_forever(poll_interval=0.25)
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
