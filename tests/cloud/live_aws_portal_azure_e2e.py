#!/usr/bin/env python3
"""Opt-in live smoke tests for the deployed portal and Azure demo WMS.

Full and module-writing tests run through SSM on an authorized EC2 instance.
The `admin-readonly` mode may also run locally against the public HTTPS FQDN
with the dedicated read-only opt-in. It reads credentials from AWS SSM
Parameter Store, never prints them, and performs only login/logout plus
read-only checks. The full mode writes compensating synthetic sale/receipt
events and verifies that the Azure demo ledger returns to its initial balance.
Targets are allowlisted; TLS verification remains enabled.
"""

from __future__ import annotations

import http.client
import http.cookiejar
import json
import math
import os
import secrets
import socket
import ssl
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPCookieProcessor,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
    urlopen,
)


ALB_ORIGIN_DNS = "tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com"
LIVE_TARGET_URLS = {
    "loopback": "http://127.0.0.1:8080",
    "alb": f"http://{ALB_ORIGIN_DNS}",
    "https": "https://tangamandapio.kendellnm.me",
    "alb-origin-https": "https://tangamandapio.kendellnm.me",
}
ADMIN_USERNAME = "admin@tangamandapio.local"
ADMIN_PARAMETER = "/tangamandapio/portal/admin-login"
ROLE_ACCOUNTS = (
    (
        "comercial",
        "comercial.demo@tangamandapio.local",
        "/tangamandapio/portal/users/comercial-demo",
        "sales",
        {
            "/api/erp/sales/orders": 200,
            "/api/outbox": 403,
            "/api/wms/inventory": 403,
            "/api/admin/users": 403,
            "/api/admin/alarm-subscriptions": 403,
        },
    ),
    (
        "operaciones",
        "operaciones.demo@tangamandapio.local",
        "/tangamandapio/portal/users/operaciones-demo",
        "operations",
        {
            "/api/erp/sales/orders": 403,
            "/api/outbox": 200,
            "/api/wms/inventory": 200,
            "/api/admin/users": 403,
            "/api/admin/alarm-subscriptions": 403,
        },
    ),
)
REGION = "us-east-1"
OPT_IN = "I_ACKNOWLEDGE_SYNTHETIC_RDS_AND_AZURE_WRITES"
READ_ONLY_OPT_IN = "I_ACKNOWLEDGE_LIVE_ADMIN_READONLY_CHECK"
ROLE_MATRIX_OPT_IN = "I_ACKNOWLEDGE_TEMPORARY_ROLE_ACCOUNT_WRITES"
FIXED_SKU = "SKU-QA-V10-20261014"
PARTNER_NAME = "QA LIVE AWS Azure v10"
REQUEST_TIMEOUT = 20
PROCESS_TIMEOUT = 20
POLL_ATTEMPTS = 25
READ_ONLY_LOAD_REQUESTS = 24
READ_ONLY_LOAD_CONCURRENCY = 6
AZURE_POISON_QUEUE_URL = "https://tangama-wms-261008.azurewebsites.net/api/wms/poison-queue"
CFN_STACK_NAME = "tangamandapio-live-20261013"
ERP_PERMISSION_SETS = {
    "erp_admin": {"master:read", "master:write", "sales:read", "sales:write", "purchase:read", "purchase:write", "finance:read", "finance:write", "reports:read"},
    "erp_sales": {"master:read", "sales:read", "sales:write", "reports:read"},
    "erp_finance": {"master:read", "sales:read", "purchase:read", "finance:read", "finance:write", "reports:read"},
    "erp_purchasing": {"master:read", "master:write", "purchase:read", "purchase:write", "reports:read"},
    "erp_master_data": {"master:read", "master:write", "reports:read"},
    "erp_auditor": {"master:read", "sales:read", "purchase:read", "finance:read", "reports:read"},
}
ERP_PERMISSION_PROBES = (
    ("master:read", "GET", "/api/erp/partners", None),
    ("master:write", "POST", "/api/erp/partners", {}),
    ("sales:read", "GET", "/api/erp/sales/orders", None),
    ("sales:write", "POST", "/api/erp/sales/orders", {}),
    ("purchase:read", "GET", "/api/erp/purchases/orders", None),
    ("purchase:write", "POST", "/api/erp/purchases/orders", {}),
    ("finance:read", "GET", "/api/erp/finance/documents", None),
    ("finance:write", "POST", "/api/erp/finance/expenses", {}),
)


class SmokeFailure(RuntimeError):
    pass


class _ALBOriginHTTPSConnection(http.client.HTTPSConnection):
    """Connect to the ALB directly but verify TLS for the public portal host."""

    def __init__(self, host: str, *, origin_host: str, **kwargs: Any) -> None:
        super().__init__(host, **kwargs)
        self.origin_host = origin_host

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self.origin_host, self.port), self.timeout, self.source_address
        )
        try:
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self.host,
            )
        except Exception:
            raw_socket.close()
            raise


class _ALBOriginHTTPSHandler(HTTPSHandler):
    """Direct-to-origin HTTPS with normal CA and hostname validation."""

    def __init__(self) -> None:
        super().__init__(context=ssl.create_default_context())

    def https_open(self, request: Request):
        return self.do_open(
            _ALBOriginHTTPSConnection,
            request,
            origin_host=ALB_ORIGIN_DNS,
            context=self._context,
        )


def resolve_live_target(target: str) -> str:
    """Resolve only the explicitly supported, non-arbitrary live test targets."""
    try:
        return LIVE_TARGET_URLS[target]
    except KeyError:
        raise SmokeFailure(
            "Unsupported live E2E target; use loopback, alb, https, or alb-origin-https."
        ) from None


def get_secure_parameter(parameter_name: str) -> str:
    try:
        result = subprocess.run(
            [
                "aws",
                "ssm",
                "get-parameter",
                "--name",
                parameter_name,
                "--with-decryption",
                "--region",
                REGION,
                "--query",
                "Parameter.Value",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=PROCESS_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SmokeFailure("Could not retrieve the QA credential from SSM.") from error
    if result.returncode != 0:
        raise SmokeFailure("The active AWS identity cannot read the QA credential.")
    # AWS CLI's text formatter appends one newline after the secret value.
    password = result.stdout.rstrip("\r\n")
    if len(password) < 12 or "\n" in password or "\r" in password:
        raise SmokeFailure("The stored QA credential has an unexpected format.")
    return password


class PortalClient:
    def __init__(self, target: str | None = None) -> None:
        self.target = target or os.environ.get("LIVE_E2E_TARGET", "loopback")
        self.base_url = resolve_live_target(self.target)
        policy = http.cookiejar.DefaultCookiePolicy(
            secure_protocols=("http", "https", "wss")
        )
        self.cookies = http.cookiejar.CookieJar(policy=policy)
        if self.target == "alb-origin-https":
            # Do not inherit an environment proxy for this explicitly selected
            # target; connect to the known ALB while preserving the domain Host
            # and TLS SNI. Certificate verification remains enabled.
            self.opener = build_opener(
                ProxyHandler({}),
                HTTPCookieProcessor(self.cookies),
                _ALBOriginHTTPSHandler(),
            )
        else:
            self.opener = build_opener(HTTPCookieProcessor(self.cookies))
        self.csrf: str | None = None

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        accepted_statuses: tuple[int, ...] = (),
    ) -> tuple[int, dict | None]:
        status, body, _ = self.request_with_headers(
            method, path, payload, accepted_statuses
        )
        return status, body

    def request_with_headers(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        accepted_statuses: tuple[int, ...] = (),
    ) -> tuple[int, dict | None, dict[str, str]]:
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if method not in {"GET", "HEAD", "OPTIONS"}:
            # Mirror the same-origin headers a real browser sends. This keeps
            # the HTTPS smoke representative and lets Cloudflare apply its
            # normal policy without weakening or bypassing the proxy.
            headers["Origin"] = self.base_url
            headers["Referer"] = f"{self.base_url}/"
            if self.csrf:
                headers["X-CSRF-Token"] = self.csrf
        req = Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with self.opener.open(req, timeout=REQUEST_TIMEOUT) as response:
                body = response.read()
                response_headers = {
                    key.lower(): value for key, value in response.headers.items()
                }
                return (
                    response.status,
                    json.loads(body) if body else None,
                    response_headers,
                )
        except HTTPError as error:
            if error.code in accepted_statuses:
                response_headers = {
                    key.lower(): value for key, value in error.headers.items()
                }
                return error.code, None, response_headers
            # Do not echo the response body; it may contain account data.
            server = (error.headers.get("server") or "").lower()
            if "cloudflare" in server:
                edge = "cloudflare"
            elif "awselb" in server:
                edge = "alb"
            elif server:
                edge = "other"
            else:
                edge = "unknown"
            ray = error.headers.get("cf-ray") or ""
            if not ray.isascii() or not ray.replace("-", "").isalnum() or len(ray) > 100:
                ray = ""
            detail = f" (edge={edge}"
            if ray:
                detail += f", cf-ray={ray}"
            detail += ")"
            raise SmokeFailure(
                f"{method} {path} returned HTTP {error.code}{detail}."
            ) from None
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise SmokeFailure(
                f"{method} {path} failed ({type(error).__name__})."
            ) from None

    def json(self, method: str, path: str, payload: dict | None = None) -> dict:
        status, body = self.request(method, path, payload)
        if not isinstance(body, dict):
            raise SmokeFailure(f"{method} {path} returned an unexpected response.")
        return body

    def login(
        self,
        username: str = ADMIN_USERNAME,
        parameter: str = ADMIN_PARAMETER,
        expected_role: str = "admin",
        password: str | None = None,
    ) -> None:
        # Login starts without a CSRF-bound session; a fresh token is issued
        # after authentication and attached to all subsequent writes.
        self.csrf = None
        status, body = self.request(
            "POST",
            "/api/auth/login",
            {
                "username": username,
                "password": password if password is not None else get_secure_parameter(parameter),
            },
        )
        if status != 200 or not isinstance(body, dict):
            raise SmokeFailure(f"The QA {expected_role} login was not accepted.")
        session = self.json("GET", "/api/auth/session")
        user = session.get("user") or {}
        if not session.get("authenticated"):
            raise SmokeFailure(f"The QA {expected_role} login did not create a session.")
        if user.get("role") != expected_role:
            raise SmokeFailure(f"The QA login did not produce the expected {expected_role} role.")
        self.csrf = session.get("csrf_token")
        if not isinstance(self.csrf, str) or len(self.csrf) < 20:
            raise SmokeFailure("The authenticated CSRF token was not issued.")

    def logout(self) -> None:
        if self.csrf:
            self.request("POST", "/api/auth/logout", {})
            self.csrf = None


def wait_for_document(
    client: PortalClient, kind: str, document_id: int, expected: str
) -> dict:
    endpoint = f"/api/erp/{kind}/orders/{document_id}/refresh"
    last_status = "unknown"
    for _ in range(POLL_ATTEMPTS):
        document = client.json("POST", endpoint, {})
        last_status = str(document.get("status", "unknown"))
        if last_status == expected:
            return document
        if last_status in {"rejected", "failed"}:
            raise SmokeFailure(f"The synthetic {kind} event was {last_status}.")
        time.sleep(2)
    raise SmokeFailure(
        f"The synthetic {kind} event did not reach {expected} (last={last_status})."
    )


def inventory_balance(client: PortalClient, sku: str) -> int | None:
    inventory = client.json("GET", "/api/wms/inventory")
    product = next(
        (item for item in inventory.get("items", []) if item.get("sku") == sku),
        None,
    )
    value = product.get("on_hand") if product else None
    return value if type(value) is int else None


def finish_receipt(
    client: PortalClient, partner_id: int, sku: str, purchase_id: int | None
) -> dict:
    """Complete or create the compensating receipt after a successful sale."""
    if purchase_id is None:
        _, purchase = client.request(
            "POST",
            "/api/erp/purchases/orders",
            {"partner_id": partner_id, "items": [{"sku": sku, "quantity": 1}]},
        )
        if not isinstance(purchase, dict) or not isinstance(purchase.get("id"), int):
            raise SmokeFailure("Could not create the compensating synthetic receipt.")
        purchase_id = purchase["id"]

    orders_status, orders = client.request("GET", "/api/erp/purchases/orders")
    if orders_status != 200 or not isinstance(orders, list):
        raise SmokeFailure("Could not inspect the synthetic purchase state.")
    order = next((row for row in orders if row.get("id") == purchase_id), None)
    if order is None:
        raise SmokeFailure("The synthetic purchase is missing from the portal.")
    if order.get("status") == "ordered":
        _, accepted = client.request(
            "POST", f"/api/erp/purchases/orders/{purchase_id}/receive", {}
        )
        if not isinstance(accepted, dict) or accepted.get("status") != "receipt_pending":
            raise SmokeFailure("The compensating synthetic receipt was not accepted.")
    elif order.get("status") not in {"receipt_pending", "received_demo", "received"}:
        raise SmokeFailure("The synthetic purchase is in an unexpected state.")
    if order.get("status") in {"received_demo", "received"}:
        return order
    return wait_for_document(client, "purchases", purchase_id, "received_demo")


def measure_read_only_database_load(client: PortalClient) -> dict:
    """Exercise authenticated read endpoints without writing business data."""
    cookie = "; ".join(f"{item.name}={item.value}" for item in client.cookies)
    if not cookie:
        raise SmokeFailure("The authenticated session cookie is unavailable.")
    paths = (
        "/api/erp/sales/orders",
        "/api/erp/purchases/orders",
        "/api/outbox",
    )

    def read_one(index: int) -> float:
        path = paths[index % len(paths)]
        request = Request(
            client.base_url + path,
            headers={"Accept": "application/json", "Cookie": cookie},
        )
        started = time.perf_counter()
        try:
            # Reuse the same target-specific opener used for the authenticated
            # session. In particular, ``alb-origin-https`` deliberately bypasses
            # Cloudflare while preserving the portal hostname for TLS/SNI; the
            # module-level ``urlopen`` would silently use the environment proxy
            # and send this load probe through Cloudflare instead.
            with client.opener.open(request, timeout=REQUEST_TIMEOUT) as response:
                if response.status != 200:
                    raise SmokeFailure(f"Read-only request to {path} returned {response.status}.")
                json.loads(response.read())
        except HTTPError as error:
            raise SmokeFailure(
                f"Read-only request to {path} returned HTTP {error.code}."
            ) from None
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise SmokeFailure(
                f"Read-only request to {path} failed ({type(error).__name__})."
            ) from None
        return (time.perf_counter() - started) * 1000

    latencies: list[float] = []
    with ThreadPoolExecutor(max_workers=READ_ONLY_LOAD_CONCURRENCY) as executor:
        futures = [
            executor.submit(read_one, index)
            for index in range(READ_ONLY_LOAD_REQUESTS)
        ]
        for future in as_completed(futures):
            latencies.append(future.result())
    ordered = sorted(latencies)
    p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
    return {
        "requests": len(latencies),
        "concurrency": READ_ONLY_LOAD_CONCURRENCY,
        "p95_ms": round(p95, 2),
        "all_http_200": True,
    }


def verify_role_authorization(target: str = "loopback") -> dict:
    results: dict[str, dict[str, int]] = {}
    for label, username, parameter, expected_role, routes in ROLE_ACCOUNTS:
        client = PortalClient(target)
        try:
            client.login(username, parameter, expected_role=expected_role)
            session = client.json("GET", "/api/auth/session")
            if (session.get("user") or {}).get("role") != expected_role:
                raise SmokeFailure(f"The {label} account resolved to an unexpected role.")
            actual: dict[str, int] = {}
            for path, expected_status in routes.items():
                status, _ = client.request(
                    "GET", path, accepted_statuses=(403,)
                )
                actual[path] = status
                if status != expected_status:
                    raise SmokeFailure(
                        f"The {label} account received HTTP {status} on {path}; expected {expected_status}."
                    )
            results[label] = actual
        finally:
            try:
                client.logout()
            except Exception:
                pass
    return results


def verify_admin_alarm_subscriptions(client: PortalClient) -> dict:
    """Verify admin can read SNS email subscriptions without exposing addresses."""
    result = client.json("GET", "/api/admin/alarm-subscriptions")
    if result.get("topic_configured") is not True:
        raise SmokeFailure("Admin alarm notifications are not configured.")
    if result.get("confirmation_required") is not True:
        raise SmokeFailure("Admin alarm subscriptions do not require confirmation.")
    subscriptions = result.get("subscriptions")
    if not isinstance(subscriptions, list):
        raise SmokeFailure("Admin alarm subscriptions returned an invalid list.")

    seen_endpoints: set[str] = set()
    confirmed = 0
    pending = 0
    for subscription in subscriptions:
        if not isinstance(subscription, dict):
            raise SmokeFailure("Admin alarm subscriptions returned an invalid record.")
        endpoint = subscription.get("endpoint")
        subscription_arn = subscription.get("subscription_arn")
        if (
            subscription.get("protocol") != "email"
            or not isinstance(endpoint, str)
            or not endpoint.strip()
            or not isinstance(subscription_arn, str)
            or not subscription_arn.strip()
        ):
            raise SmokeFailure("Admin alarm subscriptions returned an invalid email record.")
        normalized_endpoint = endpoint.strip().casefold()
        if normalized_endpoint in seen_endpoints:
            raise SmokeFailure("Admin alarm subscriptions contain duplicate email records.")
        seen_endpoints.add(normalized_endpoint)

        status = subscription.get("status")
        if status == "confirmed":
            confirmed += 1
        elif status == "pending_confirmation":
            pending += 1
        else:
            raise SmokeFailure("Admin alarm subscriptions returned an unknown confirmation state.")

    return {
        "topic_configured": True,
        "confirmation_required": True,
        "subscription_count": len(subscriptions),
        "confirmed_count": confirmed,
        "pending_confirmation_count": pending,
    }


def inspect_admin_dashboard_consistency(client: PortalClient) -> dict:
    """Check that dashboard totals agree with the visible admin API rows."""
    dashboard = client.json("GET", "/api/dashboard")
    if dashboard.get("role") != "admin":
        raise SmokeFailure("The dashboard summary did not resolve to the admin role.")
    order_count = dashboard.get("orders")
    outbox_summary = dashboard.get("outbox")
    if (
        type(order_count) is not int
        or order_count < 0
        or not isinstance(outbox_summary, dict)
    ):
        raise SmokeFailure("The dashboard returned invalid aggregate counters.")
    pending = outbox_summary.get("pending")
    delivered = outbox_summary.get("delivered")
    if any(type(value) is not int or value < 0 for value in (pending, delivered)):
        raise SmokeFailure("The dashboard returned invalid outbox counters.")

    orders_status, orders = client.request("GET", "/api/orders")
    if (
        orders_status != 200
        or not isinstance(orders, list)
    ):
        raise SmokeFailure("Admin order rows were unavailable for reconciliation.")
    if order_count < len(orders):
        raise SmokeFailure("The dashboard order counter is lower than its visible order rows.")
    if len(orders) < 50 and order_count != len(orders):
        raise SmokeFailure("The dashboard order total differs from the complete visible order list.")

    page_size = 30
    outbox: list[dict] = []
    total: int | None = None
    offset = 0
    while total is None or offset < total:
        outbox_status, page, page_headers = client.request_with_headers(
            "GET", f"/api/outbox?limit={page_size}&offset={offset}"
        )
        if outbox_status != 200 or not isinstance(page, list):
            raise SmokeFailure("Admin outbox page was unavailable for reconciliation.")
        try:
            page_total = int(page_headers["x-total-count"])
            reported_limit = int(page_headers["x-page-limit"])
            reported_offset = int(page_headers["x-page-offset"])
        except (KeyError, TypeError, ValueError):
            raise SmokeFailure("Admin outbox pagination metadata was invalid.") from None
        if (
            page_total < 0
            or page_total > 10_000
            or reported_limit != page_size
            or reported_offset != offset
            or len(page) > page_size
            or (total is not None and page_total != total)
        ):
            raise SmokeFailure("Admin outbox pagination metadata was inconsistent.")
        total = page_total
        outbox.extend(page)
        if len(page) < page_size and len(outbox) < total:
            raise SmokeFailure("Admin outbox pagination ended before the reported total.")
        offset += len(page)
        if not page and offset < total:
            raise SmokeFailure("Admin outbox pagination returned an empty page before the total.")
    event_ids = [row.get("event_id") for row in outbox]
    if len(event_ids) != len(set(event_ids)) or len(outbox) != total:
        raise SmokeFailure("Admin outbox pages contained duplicates or omitted events.")

    pending_rows = sum(row.get("status") != "delivered" for row in outbox)
    delivered_rows = sum(row.get("status") == "delivered" for row in outbox)
    if pending < pending_rows or delivered < delivered_rows:
        raise SmokeFailure("Dashboard outbox totals are lower than the visible event rows.")
    if pending != pending_rows or delivered != delivered_rows:
        raise SmokeFailure("Dashboard outbox counters differ from the complete event list.")
    return {
        "order_count": order_count,
        "visible_orders": len(orders),
        "orders_match_complete_list": len(orders) < 50,
        "outbox_pending": pending,
        "outbox_delivered": delivered,
        "visible_outbox_rows": len(outbox),
        "outbox_total": total,
        "outbox_reconciliation": "complete_paginated",
    }


def main_admin_readonly_smoke(target: str) -> int:
    try:
        client = PortalClient(target)
    except SmokeFailure as error:
        print(f"Refused: {error}")
        return 2
    try:
        roles = verify_role_authorization(target)
        client.login()
        access = client.json("GET", "/api/erp/access")
        if "erp_admin" not in access.get("roles", []):
            raise SmokeFailure("The authenticated account lacks the ERP admin role.")
        dashboard = inspect_admin_dashboard_consistency(client)
        alarms = verify_admin_alarm_subscriptions(client)
        recording_playback = verify_saved_voice_recording_playback(client)
        read_load = measure_read_only_database_load(client)
        print(
            json.dumps(
                {
                    "result": "LIVE_ADMIN_READONLY_SMOKE_PASSED",
                    "target": client.target,
                    "role_authorization": roles,
                    "dashboard": dashboard,
                    "alarm_subscriptions": alarms,
                    "recording_playback": recording_playback,
                    "read_only_load": read_load,
                    "alarm_triggered": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except SmokeFailure as error:
        print(f"LIVE_ADMIN_READONLY_SMOKE_FAILED: {error}")
        return 1
    finally:
        client.logout()


def verify_saved_voice_recording_playback(client: PortalClient) -> dict[str, Any]:
    """Verify one consented recording through the same private portal route as the UI."""
    status, catalog = client.request("GET", "/api/voice/recordings")
    if status != 200 or not isinstance(catalog, dict):
        raise SmokeFailure("The authenticated voice recording catalog was unavailable.")
    recordings = catalog.get("recordings")
    if not isinstance(recordings, list):
        raise SmokeFailure("The voice recording catalog returned an unexpected response.")
    if not recordings:
        return {"saved_recordings": 0, "playback": "no_saved_recordings"}

    recording = recordings[0]
    file_url = recording.get("file_url") if isinstance(recording, dict) else None
    if (
        not isinstance(file_url, str)
        or not file_url.startswith("/api/voice/recordings/")
        or not file_url.endswith("/file")
    ):
        raise SmokeFailure("The saved recording did not contain a same-origin file route.")
    try:
        request = Request(
            client.base_url + file_url,
            headers={"Accept": "*/*"},
            method="GET",
        )
        with client.opener.open(request, timeout=REQUEST_TIMEOUT) as response:
            content = response.read()
            content_type = (
                response.headers.get("Content-Type", "")
                .split(";", 1)[0]
                .lower()
            )
            response_status = response.status
    except HTTPError as error:
        raise SmokeFailure(
            f"Saved voice recording playback returned HTTP {error.code}."
        ) from None
    except (URLError, TimeoutError) as error:
        raise SmokeFailure(
            f"Saved voice recording playback failed ({type(error).__name__})."
        ) from None

    expected_size = recording.get("size_bytes")
    if (
        response_status != 200
        or not content
        or not content_type.startswith("audio/")
        or type(expected_size) is not int
        or len(content) != expected_size
    ):
        raise SmokeFailure("Saved voice recording playback returned invalid media or size.")
    return {
        "saved_recordings": len(recordings),
        "playback": "passed",
        "bytes": len(content),
        "content_type": content_type,
    }


def main_admin_recording_readonly_smoke(target: str) -> int:
    """Check one saved recording without running unrelated role/dashboard probes."""
    try:
        client = PortalClient(target)
    except SmokeFailure as error:
        print(f"Refused: {error}")
        return 2
    try:
        client.login()
        playback = verify_saved_voice_recording_playback(client)
        if playback.get("playback") != "passed":
            raise SmokeFailure("No saved audio was available for the playback check.")
        print(
            json.dumps(
                {
                    "result": "LIVE_ADMIN_RECORDING_READONLY_SMOKE_PASSED",
                    "target": client.target,
                    "recording_playback": playback,
                },
                sort_keys=True,
            )
        )
        return 0
    except SmokeFailure as error:
        print(f"LIVE_ADMIN_RECORDING_READONLY_SMOKE_FAILED: {error}")
        return 1
    finally:
        client.logout()


def exercise_erp_role_matrix(admin: PortalClient) -> dict:
    """Probe live ERP permissions; deactivate temporary accounts in all cases."""
    users_status, users = admin.request("GET", "/api/admin/users")
    if users_status != 200 or not isinstance(users, list):
        raise SmokeFailure("The admin user directory returned an unexpected response.")
    admin_record = next(
        (
            user for user in users
            if user.get("username") == ADMIN_USERNAME and user.get("role") == "admin"
        ),
        None,
    )
    if not isinstance(admin_record, dict) or type(admin_record.get("company_id")) is not int:
        raise SmokeFailure("Could not resolve the admin tenant for temporary role checks.")

    temporary_users: list[dict[str, Any]] = []
    role_clients: dict[str, PortalClient] = {"erp_admin": admin}
    run_id = f"{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{secrets.token_hex(3)}"
    cleanup_failed = False
    try:
        commercial = PortalClient(admin.target)
        commercial.login(
            username=ROLE_ACCOUNTS[0][1],
            parameter=ROLE_ACCOUNTS[0][2],
            expected_role=ROLE_ACCOUNTS[0][3],
        )
        role_clients["erp_sales"] = commercial

        for role_code in ("erp_finance", "erp_purchasing", "erp_master_data", "erp_auditor"):
            username = f"qa-{role_code}-{run_id}@tangamandapio.local"
            password = secrets.token_urlsafe(32)
            portal_role = "auditor" if role_code == "erp_auditor" else "sales"
            temporary_users.append({"id": None, "username": username})
            create_status, created = admin.request(
                "POST",
                "/api/admin/users",
                {
                    "username": username,
                    "password": password,
                    "role": portal_role,
                    "company_id": admin_record["company_id"],
                },
                accepted_statuses=(400, 403, 409),
            )
            created_user = created.get("user") if isinstance(created, dict) else None
            user_id = created_user.get("id") if isinstance(created_user, dict) else None
            if create_status != 201 or type(user_id) is not int:
                raise SmokeFailure("Could not create a temporary ERP role-check account.")
            temporary_users[-1]["id"] = user_id

            assigned_status, _ = admin.request(
                "PUT",
                f"/api/erp/users/{user_id}/roles",
                {"roles": [role_code]},
                accepted_statuses=(400, 403, 404),
            )
            if assigned_status != 200:
                raise SmokeFailure("Could not assign the temporary ERP role.")

            role_client = PortalClient(admin.target)
            role_client.login(
                username=username,
                expected_role=portal_role,
                password=password,
            )
            role_clients[role_code] = role_client

        results: dict[str, dict[str, int]] = {}
        for role_code, role_client in role_clients.items():
            access = role_client.json("GET", "/api/erp/access")
            if role_code not in access.get("roles", []):
                raise SmokeFailure(f"The live {role_code} account has an unexpected ERP role.")
            statuses: dict[str, int] = {}
            for permission, method, path, payload in ERP_PERMISSION_PROBES:
                allowed = permission in ERP_PERMISSION_SETS[role_code]
                expected = (200 if method == "GET" else 400) if allowed else 403
                status, _ = role_client.request(
                    method,
                    path,
                    payload,
                    accepted_statuses=(400, 403),
                )
                statuses[f"{method} {path}"] = status
                if status != expected:
                    raise SmokeFailure(
                        f"The live {role_code} account received HTTP {status} on {path}; expected {expected}."
                    )
            results[role_code] = statuses
        return {
            "roles": results,
            "probe_count": sum(len(statuses) for statuses in results.values()),
            "temporary_account_count": len(temporary_users),
        }
    finally:
        for role_code, role_client in role_clients.items():
            if role_code != "erp_admin":
                try:
                    role_client.logout()
                except Exception:
                    pass
        for user in temporary_users:
            try:
                user_id = user.get("id")
                if type(user_id) is not int:
                    candidates_status, candidates = admin.request("GET", "/api/admin/users")
                    if candidates_status != 200 or not isinstance(candidates, list):
                        raise SmokeFailure("Could not inspect the admin user directory for cleanup.")
                    matching = next(
                        (candidate for candidate in candidates if candidate.get("username") == user["username"]),
                        None,
                    )
                    user_id = matching.get("id") if isinstance(matching, dict) else None
                    if type(user_id) is int:
                        user["id"] = user_id
                if type(user_id) is not int:
                    continue
                status, _ = admin.request(
                    "PATCH",
                    f"/api/admin/users/{user_id}",
                    {"active": False},
                    accepted_statuses=(400, 403, 404),
                )
                if status != 200:
                    cleanup_failed = True
            except SmokeFailure:
                cleanup_failed = True
        if temporary_users:
            try:
                final_status, final_users = admin.request("GET", "/api/admin/users")
                if final_status != 200 or not isinstance(final_users, list):
                    raise SmokeFailure("Could not verify temporary ERP account cleanup.")
                by_id = {user.get("id"): user for user in final_users if isinstance(user, dict)}
                if any(
                    type(user.get("id")) is int
                    and by_id.get(user["id"], {}).get("active") is not False
                    for user in temporary_users
                ):
                    cleanup_failed = True
            except SmokeFailure:
                cleanup_failed = True
        if cleanup_failed:
            raise SmokeFailure("Temporary ERP role-check accounts could not all be confirmed inactive.")


def main_admin_role_matrix(target: str) -> int:
    try:
        admin = PortalClient(target)
    except SmokeFailure as error:
        print(f"Refused: {error}")
        return 2
    try:
        admin.login()
        result = exercise_erp_role_matrix(admin)
        print(
            json.dumps(
                {
                    "result": "LIVE_ADMIN_ERP_ROLE_MATRIX_PASSED",
                    "target": admin.target,
                    **result,
                    "temporary_accounts_deactivated": result["temporary_account_count"],
                },
                sort_keys=True,
            )
        )
        return 0
    except SmokeFailure as error:
        print(f"LIVE_ADMIN_ERP_ROLE_MATRIX_FAILED: {error}")
        return 1
    finally:
        admin.logout()


def exercise_finance_workflow(client: PortalClient) -> dict:
    """Create and settle a tiny synthetic payable; this is not a real payment."""
    reference = (
        f"QA-CLOUD-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-"
        f"{secrets.token_hex(3).upper()}"
    )
    amount = 0.05
    status, expense = client.request(
        "POST",
        "/api/erp/finance/expenses",
        {
            "description": "Prueba cloud sintética de Finanzas",
            "amount": amount,
            "reference": reference,
        },
    )
    if status != 201 or not isinstance(expense, dict) or not isinstance(expense.get("id"), int):
        raise SmokeFailure("The synthetic finance expense was not durably accepted.")

    document_id = expense["id"]
    settle_status, settled = client.request(
        "POST", f"/api/erp/finance/documents/{document_id}/settle", {}
    )
    if settle_status not in {200, 201} or not isinstance(settled, dict) or settled.get("status") != "paid":
        raise SmokeFailure("The synthetic finance expense did not settle in the portal ledger.")

    list_status, documents = client.request("GET", "/api/erp/finance/documents")
    if list_status != 200 or not isinstance(documents, list):
        raise SmokeFailure("The finance document list returned an unexpected response.")
    stored = next((row for row in documents if row.get("id") == document_id), None)
    if not stored or stored.get("status") != "paid" or stored.get("reference") != reference:
        raise SmokeFailure("The settled synthetic finance document was not persisted.")
    return {"status": "paid", "amount": amount}


def exercise_internal_portal_mail(client: PortalClient) -> dict:
    """Test private inbox delivery only when no external SMTP relay is active."""
    mail_status = client.json("GET", "/api/erp/mail/status")
    smtp_configured = mail_status.get("smtp_configured")
    if type(smtp_configured) is not bool:
        raise SmokeFailure("The mail transport status did not report SMTP configuration.")
    if smtp_configured:
        # Do not send an unapproved message through a production SMTP relay.
        return {"status": "not_sent_smtp_relay_configured", "smtp_configured": True}
    if mail_status.get("transport") != "portal_only":
        raise SmokeFailure("The mail service did not confirm portal-only delivery mode.")

    users_status, users = client.request("GET", "/api/erp/mail/users")
    if users_status != 200 or not isinstance(users, list):
        raise SmokeFailure("The internal mail directory returned an unexpected response.")
    commercial_username = ROLE_ACCOUNTS[0][1]
    recipient = next(
        (row for row in users if row.get("username") == commercial_username), None
    )
    if not recipient or not isinstance(recipient.get("id"), int):
        raise SmokeFailure("The synthetic commercial mailbox is unavailable.")

    subject = (
        f"[QA] Prueba interna {datetime.now(timezone.utc):%Y%m%d%H%M%S}-"
        f"{secrets.token_hex(3).upper()}"
    )
    body = "Mensaje sintético de prueba cloud; no enviar fuera del portal."
    create_status, message = client.request(
        "POST",
        "/api/erp/mail",
        {"recipient_id": recipient["id"], "subject": subject, "body": body},
    )
    if (
        create_status != 201
        or not isinstance(message, dict)
        or not isinstance(message.get("id"), int)
        or message.get("status") != "sent_internal"
        or message.get("smtp_status") != "portal_only"
    ):
        raise SmokeFailure("The message was not stored in portal-only mail mode.")
    message_id = message["id"]

    sent_status, sent = client.request("GET", "/api/erp/mail?folder=sent")
    if sent_status != 200 or not isinstance(sent, list) or not any(
        row.get("id") == message_id and row.get("subject") == subject for row in sent
    ):
        raise SmokeFailure("The synthetic message is missing from the sender's sent folder.")

    recipient_client = PortalClient(client.target)
    try:
        recipient_client.login(
            username=commercial_username,
            parameter=ROLE_ACCOUNTS[0][2],
            expected_role=ROLE_ACCOUNTS[0][3],
        )
        inbox_status, inbox = recipient_client.request("GET", "/api/erp/mail?folder=inbox")
        received = next(
            (row for row in inbox if row.get("id") == message_id), None
        ) if isinstance(inbox, list) else None
        if (
            inbox_status != 200
            or not received
            or received.get("subject") != subject
            or received.get("body") != body
            or received.get("unread") is not True
        ):
            raise SmokeFailure("The synthetic message did not arrive unread in the recipient inbox.")
        read_status, read_result = recipient_client.request(
            "POST", f"/api/erp/mail/{message_id}/read", {}
        )
        if read_status not in {200, 201} or not isinstance(read_result, dict) or read_result.get("read") is not True:
            raise SmokeFailure("The recipient could not mark the synthetic message as read.")
        return {"status": "portal_only_sent_and_read", "smtp_configured": False}
    finally:
        recipient_client.logout()


def _aws_cli_text(arguments: list[str], failure_message: str) -> str:
    try:
        result = subprocess.run(
            ["aws", *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=PROCESS_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SmokeFailure(failure_message) from error
    if result.returncode != 0:
        raise SmokeFailure(failure_message)
    return result.stdout.rstrip("\r\n")


def inspect_azure_poison_queue() -> dict:
    """Read only the Azure poison queue's approximate count; never touch messages."""
    secret_name = _aws_cli_text(
        [
            "cloudformation",
            "describe-stacks",
            "--stack-name",
            CFN_STACK_NAME,
            "--region",
            REGION,
            "--query",
            "Stacks[0].Parameters[?ParameterKey=='AzureFunctionKeySecret'].ParameterValue | [0]",
            "--output",
            "text",
        ],
        "Could not resolve the Azure Function-key secret reference from CloudFormation.",
    )
    if not secret_name or secret_name == "None":
        raise SmokeFailure("The Azure Function-key secret reference is not configured.")
    function_key = _aws_cli_text(
        [
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            secret_name,
            "--region",
            REGION,
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
        "The EC2 instance role cannot read the Azure Function-key secret.",
    )
    if len(function_key) < 12 or "\n" in function_key or "\r" in function_key:
        raise SmokeFailure("The Azure Function key has an unexpected format.")

    request = Request(
        AZURE_POISON_QUEUE_URL,
        headers={"Accept": "application/json", "x-functions-key": function_key},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            if response.status != 200:
                raise SmokeFailure("The Azure poison-queue status endpoint returned an unexpected status.")
            payload = json.loads(response.read())
    except HTTPError as error:
        raise SmokeFailure(
            f"The Azure poison-queue status endpoint returned HTTP {error.code}."
        ) from None
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SmokeFailure(
            f"The Azure poison-queue status request failed ({type(error).__name__})."
        ) from None
    count = payload.get("approximate_message_count") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "ok"
        or payload.get("queue") != "fulfillment-events-poison"
        or type(count) is not int
        or count < 0
        or payload.get("payloads_exposed") is not False
    ):
        raise SmokeFailure("Azure did not return a safe poison-queue count.")
    return {"status": "ok", "approximate_message_count": count, "payloads_exposed": False}


def main_admin_module_smoke(target: str) -> int:
    try:
        client = PortalClient(target)
    except SmokeFailure as error:
        print(f"Refused: {error}")
        return 2
    try:
        client.login()
        access = client.json("GET", "/api/erp/access")
        if "erp_admin" not in access.get("roles", []):
            raise SmokeFailure("The authenticated account lacks the ERP admin role.")
        poison_queue = inspect_azure_poison_queue()
        finance = exercise_finance_workflow(client)
        mail = exercise_internal_portal_mail(client)
        print(
            json.dumps(
                {
                    "result": "LIVE_ADMIN_MODULE_SMOKE_PASSED",
                    "target": client.target,
                    "finance": finance,
                    "internal_mail": mail,
                    "azure_poison_queue": poison_queue,
                },
                sort_keys=True,
            )
        )
        return 0
    except SmokeFailure as error:
        print(f"LIVE_ADMIN_MODULE_SMOKE_FAILED: {error}")
        return 1
    finally:
        client.logout()


def exercise_duplicate_outbox_delivery(client: PortalClient) -> dict:
    """Replay one completed synthetic event and verify the demo ledger is unchanged."""
    before_inventory = client.json("GET", "/api/wms/inventory")
    if before_inventory.get("mode") != "demo-inventory-ledger":
        raise SmokeFailure("Refusing duplicate delivery against a non-demo inventory.")
    before_stock = {
        item.get("sku"): item.get("on_hand")
        for item in before_inventory.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("sku"), str)
    }

    list_status, events = client.request("GET", "/api/outbox?limit=100&offset=0")
    if list_status != 200 or not isinstance(events, list):
        raise SmokeFailure("The outbox could not be read for duplicate-delivery testing.")

    selected: dict[str, Any] | None = None
    initial_fulfillment: str | None = None
    for event in events:
        if not isinstance(event, dict) or event.get("status") != "delivered":
            continue
        event_id = event.get("event_id")
        attempts = event.get("attempts")
        if not isinstance(event_id, str) or type(attempts) is not int:
            continue
        status, fulfillment = client.request(
            "GET", f"/api/outbox/{event_id}/fulfillment-status"
        )
        if (
            status == 200
            and isinstance(fulfillment, dict)
            and fulfillment.get("fulfillment_status")
            in {"demo_fulfillment_completed", "demo_restock_completed"}
        ):
            selected = event
            initial_fulfillment = fulfillment["fulfillment_status"]
            break
    if selected is None or initial_fulfillment is None:
        raise SmokeFailure("No completed synthetic Azure event is available to replay.")

    event_id = selected["event_id"]
    previous_attempts = selected["attempts"]
    retry_status, retry = client.request("POST", f"/api/outbox/{event_id}/retry", {})
    if (
        retry_status != 200
        or not isinstance(retry, dict)
        or retry.get("status") != "delivered"
        or retry.get("upstream") != "queued_duplicate"
    ):
        raise SmokeFailure("Azure did not acknowledge the replay as a duplicate event.")

    final_status, final_events = client.request("GET", "/api/outbox?limit=100&offset=0")
    final_event = next(
        (
            row for row in final_events
            if isinstance(row, dict) and row.get("event_id") == event_id
        ),
        None,
    ) if isinstance(final_events, list) else None
    if (
        final_status != 200
        or not isinstance(final_event, dict)
        or final_event.get("status") != "delivered"
        or final_event.get("attempts") != previous_attempts + 1
    ):
        raise SmokeFailure("The duplicate outbox attempt was not durably reconciled.")

    time.sleep(3)
    after_inventory = client.json("GET", "/api/wms/inventory")
    after_stock = {
        item.get("sku"): item.get("on_hand")
        for item in after_inventory.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("sku"), str)
    }
    if after_inventory.get("mode") != "demo-inventory-ledger" or after_stock != before_stock:
        raise SmokeFailure("Replaying a completed event changed the synthetic ledger stock.")

    status, fulfillment = client.request(
        "GET", f"/api/outbox/{event_id}/fulfillment-status"
    )
    if (
        status != 200
        or not isinstance(fulfillment, dict)
        or fulfillment.get("fulfillment_status") != initial_fulfillment
    ):
        raise SmokeFailure("The completed Azure event status changed after duplicate delivery.")

    return {
        "event_id": event_id,
        "initial_status": initial_fulfillment,
        "retry_upstream": retry["upstream"],
        "attempts_before": previous_attempts,
        "attempts_after": final_event["attempts"],
        "inventory_unchanged": True,
        "inventory_mode": "demo-inventory-ledger",
    }


def main_admin_idempotency_smoke(target: str) -> int:
    try:
        client = PortalClient(target)
    except SmokeFailure as error:
        print(f"Refused: {error}")
        return 2
    try:
        client.login()
        access = client.json("GET", "/api/erp/access")
        if "erp_admin" not in access.get("roles", []):
            raise SmokeFailure("The authenticated account lacks the ERP admin role.")
        result = exercise_duplicate_outbox_delivery(client)
        print(
            json.dumps(
                {
                    "result": "LIVE_ADMIN_IDEMPOTENCY_SMOKE_PASSED",
                    "target": client.target,
                    **result,
                },
                sort_keys=True,
            )
        )
        return 0
    except SmokeFailure as error:
        print(f"LIVE_ADMIN_IDEMPOTENCY_SMOKE_FAILED: {error}")
        return 1
    finally:
        client.logout()


def main() -> int:
    target = os.environ.get("LIVE_E2E_TARGET", "loopback")
    mode = os.environ.get("LIVE_E2E_MODE", "full")
    if mode not in {"full", "admin-readonly", "admin-recording-readonly", "admin-modules", "admin-role-matrix", "admin-idempotency"}:
        print("Refused: use the approved full, admin-readonly, admin-recording-readonly, admin-modules, admin-role-matrix, or admin-idempotency test mode.")
        return 2
    expected_opt_in = (
        READ_ONLY_OPT_IN if mode in {"admin-readonly", "admin-recording-readonly"}
        else ROLE_MATRIX_OPT_IN if mode == "admin-role-matrix"
        else OPT_IN
    )
    if os.environ.get("RUN_LIVE_DEPLOYED_E2E") != expected_opt_in:
        print("Refused: set the exact opt-in appropriate to this live test mode.")
        return 2
    if mode == "admin-readonly":
        return main_admin_readonly_smoke(target)
    if mode == "admin-recording-readonly":
        return main_admin_recording_readonly_smoke(target)
    if mode == "admin-role-matrix":
        return main_admin_role_matrix(target)
    if mode == "admin-modules":
        return main_admin_module_smoke(target)
    if mode == "admin-idempotency":
        return main_admin_idempotency_smoke(target)
    try:
        client = PortalClient(target)
    except SmokeFailure as error:
        print(f"Refused: {error}")
        return 2
    sku: str | None = None
    baseline: int | None = None
    partner_id: int | None = None
    sale_id: int | None = None
    sale_result: dict | None = None
    purchase_id: int | None = None
    purchase_result: dict | None = None
    role_matrix: dict | None = None
    alarm_subscription_check: dict | None = None
    try:
        role_matrix = verify_role_authorization(target)
        client.login()
        access = client.json("GET", "/api/erp/access")
        if "erp_admin" not in access.get("roles", []):
            raise SmokeFailure("The authenticated account lacks the ERP admin role.")
        alarm_subscription_check = verify_admin_alarm_subscriptions(client)

        inventory = client.json("GET", "/api/wms/inventory")
        if inventory.get("mode") != "demo-inventory-ledger" or inventory.get("is_real_erp") is not False:
            raise SmokeFailure("Refusing to mutate an inventory not marked synthetic.")

        existing_items = inventory.get("items", [])
        sku = FIXED_SKU
        existing = next(
            (item for item in existing_items if item.get("sku") == sku), None
        )
        if existing and (type(existing.get("on_hand")) is not int or existing["on_hand"] < 1):
            sku = f"SKU-QAV10-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"
            existing = None
        initial_stock = existing["on_hand"] if existing else 10

        imported = client.json(
            "POST",
            "/api/erp/products/import",
            {
                "products": [
                    {
                        "sku": sku,
                        "name": "Artículo sintético de prueba v10",
                        "unit": "unidad",
                        "sale_price": 1.00,
                        "purchase_cost": 0.75,
                        "initial_stock": initial_stock,
                    }
                ]
            },
        )
        if imported.get("imported") != 1 or imported.get("stock_preserved") is not True:
            raise SmokeFailure("The synthetic catalog import did not confirm stock protection.")
        if not existing and imported.get("created") != 1:
            raise SmokeFailure("The isolated QA SKU was not created as expected.")

        inventory = client.json("GET", "/api/wms/inventory")
        if inventory.get("mode") != "demo-inventory-ledger":
            raise SmokeFailure("Azure stopped identifying the ledger as synthetic.")
        product = next(
            (item for item in inventory.get("items", []) if item.get("sku") == sku),
            None,
        )
        if not product or type(product.get("on_hand")) is not int:
            raise SmokeFailure("The imported synthetic SKU is missing from Azure inventory.")
        baseline = product["on_hand"]
        if baseline < 1:
            raise SmokeFailure("The synthetic SKU has insufficient demo stock for the sale.")

        partner_status, partners = client.request("GET", "/api/erp/partners")
        if partner_status != 200 or not isinstance(partners, list):
            raise SmokeFailure("The ERP partner directory returned an unexpected response.")
        partner = next(
            (
                item
                for item in partners
                if item.get("active")
                and item.get("kind") == "both"
                and item.get("name") == PARTNER_NAME
            ),
            None,
        )
        if partner is None:
            _, created = client.request(
                "POST",
                "/api/erp/partners",
                {"kind": "both", "name": PARTNER_NAME},
            )
            if not isinstance(created, dict) or not isinstance(created.get("id"), int):
                raise SmokeFailure("The synthetic QA partner could not be created.")
            partner_id = created["id"]
        else:
            partner_id = partner["id"]

        _, sale = client.request(
            "POST",
            "/api/erp/sales/orders",
            {"partner_id": partner_id, "items": [{"sku": sku, "quantity": 1}]},
        )
        if not isinstance(sale, dict) or not isinstance(sale.get("id"), int):
            raise SmokeFailure("The synthetic sale was not durably accepted.")
        sale_id = sale["id"]
        sale_result = wait_for_document(client, "sales", sale_id, "completed_demo")

        _, purchase = client.request(
            "POST",
            "/api/erp/purchases/orders",
            {"partner_id": partner_id, "items": [{"sku": sku, "quantity": 1}]},
        )
        if not isinstance(purchase, dict) or not isinstance(purchase.get("id"), int):
            raise SmokeFailure("The synthetic purchase was not durably accepted.")
        purchase_id = purchase["id"]
        _, received = client.request(
            "POST", f"/api/erp/purchases/orders/{purchase_id}/receive", {}
        )
        if not isinstance(received, dict) or received.get("status") != "receipt_pending":
            raise SmokeFailure("The synthetic purchase receipt was not accepted.")
        purchase_result = wait_for_document(
            client, "purchases", purchase_id, "received_demo"
        )

        final_inventory = client.json("GET", "/api/wms/inventory")
        final_product = next(
            (
                item
                for item in final_inventory.get("items", [])
                if item.get("sku") == sku
            ),
            None,
        )
        final_stock = final_product.get("on_hand") if final_product else None
        if final_stock != baseline:
            raise SmokeFailure(
                f"Synthetic ledger did not return to its baseline ({baseline} -> {final_stock})."
            )

        outbox_status, outbox = client.request("GET", "/api/outbox")
        if outbox_status != 200 or not isinstance(outbox, list):
            raise SmokeFailure("The protected outbox view returned an unexpected response.")
        event_ids = {sale_result.get("event_id"), purchase_result.get("event_id")}
        delivered_ids = {
            row.get("event_id")
            for row in outbox
            if row.get("status") == "delivered"
        }
        if not event_ids.issubset(delivered_ids):
            raise SmokeFailure("The sale and receipt outbox events are not both delivered.")

        read_load = measure_read_only_database_load(client)

        print(
            json.dumps(
                {
                    "result": "LIVE_E2E_PASSED",
                    "target": client.target,
                    "database_health": "ok",
                    "portal_role": "admin",
                    "azure_mode": final_inventory.get("mode"),
                    "sku": sku,
                    "catalog_import": "passed",
                    "sale_status": sale_result.get("status"),
                    "purchase_status": purchase_result.get("status"),
                    "outbox_delivered": 2,
                    "synthetic_stock_baseline": baseline,
                    "synthetic_stock_final": final_stock,
                    "read_only_database_load": read_load,
                    "role_authorization_checks": role_matrix,
                    "admin_alarm_subscription_check": alarm_subscription_check,
                },
                sort_keys=True,
            )
        )
        return 0
    except SmokeFailure as error:
        compensation = "not_needed"
        if sale_id is not None and sale_result is None:
            try:
                sale_result = wait_for_document(
                    client, "sales", sale_id, "completed_demo"
                )
            except SmokeFailure:
                compensation = "sale_state_uncertain_inspect_before_retry"
        if (
            sale_result is not None
            and sale_result.get("status") == "completed_demo"
            and purchase_result is None
            and partner_id is not None
            and sku is not None
        ):
            try:
                finish_receipt(client, partner_id, sku, purchase_id)
                compensation = "synthetic_stock_receipt_completed"
            except SmokeFailure:
                compensation = "receipt_recovery_failed_inspect_ledger"
        print(f"LIVE_E2E_FAILED: {error}; compensation={compensation}")
        return 1
    finally:
        try:
            client.logout()
        except Exception:
            # Do not replace the actual test result with logout cleanup output.
            pass


if __name__ == "__main__":
    sys.exit(main())
