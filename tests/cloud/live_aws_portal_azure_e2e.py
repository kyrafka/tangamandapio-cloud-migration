#!/usr/bin/env python3
"""Opt-in end-to-end smoke from a deployed AWS portal instance to Azure.

Run only through SSM on an authorized Tangamandapio EC2 instance. It reads the
admin password from that instance's SSM role, creates/reuses a synthetic QA
partner and SKU, sells one unit, receives one unit, and requires the Azure demo
ledger to return to its initial balance. The target is restricted to loopback,
the known public ALB, or the configured HTTPS portal domain (through Cloudflare
or directly to the ALB with hostname-validated TLS). It never prints
credentials or API responses containing personal data.
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
FIXED_SKU = "SKU-QA-V10-20261014"
PARTNER_NAME = "QA LIVE AWS Azure v10"
REQUEST_TIMEOUT = 20
PROCESS_TIMEOUT = 20
POLL_ATTEMPTS = 25
READ_ONLY_LOAD_REQUESTS = 24
READ_ONLY_LOAD_CONCURRENCY = 6


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
            check_hostname=True,
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
        raise SmokeFailure("The EC2 instance role cannot read the QA credential.")
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
                return response.status, json.loads(body) if body else None
        except HTTPError as error:
            if error.code in accepted_statuses:
                return error.code, None
            # Do not echo the response body; it may contain account data.
            raise SmokeFailure(f"{method} {path} returned HTTP {error.code}.") from None
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
    ) -> None:
        # Login starts without a CSRF-bound session; a fresh token is issued
        # after authentication and attached to all subsequent writes.
        self.csrf = None
        status, body = self.request(
            "POST",
            "/api/auth/login",
            {"username": username, "password": get_secure_parameter(parameter)},
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


def main() -> int:
    if os.environ.get("RUN_LIVE_DEPLOYED_E2E") != OPT_IN:
        print("Refused: set the exact opt-in only for the approved live synthetic smoke.")
        return 2
    target = os.environ.get("LIVE_E2E_TARGET", "loopback")
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
