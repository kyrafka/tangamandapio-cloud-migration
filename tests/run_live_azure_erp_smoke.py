"""Opt-in live AWS-release ERP -> Azure WMS smoke test with compensation.

This test runs the local AWS release artifact against Azure, creates only
temporary local ERP records and synthetic Azure event blobs, and restores the
one demo-ledger unit it sells. It refuses to run without an explicit opt-in and
validates the subscription, resource group, function name, and demo-ledger mode
before writing anything. It does not invoke the deployed AWS instance.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_GROUP = "rg-tangamandapio-rebuild-wus"
FUNCTION_APP = "tangama-wms-261008"
SKU = "SKU-ARROZ-001"
OPT_IN_VALUE = "I_ACKNOWLEDGE_DEMO_STOCK_MUTATION"
# Management-plane reads (especially Function keys) can take ~25s in the
# student subscription; retain a finite bound without aborting a valid lookup.
AZURE_CLI_TIMEOUT_SECONDS = 90
AZURE_ARM_TIMEOUT_SECONDS = 60
POLL_SECONDS = 150


class SmokeFailure(RuntimeError):
    pass


class AzureTransientReadError(SmokeFailure):
    """A read can be retried without repeating the event mutation."""


def azure_cli(*args: str) -> str:
    command = shutil.which("az.cmd") or shutil.which("az")
    if not command:
        raise SmokeFailure("Azure CLI was not found on PATH.")
    if os.name == "nt" and command.lower().endswith(".cmd"):
        # Invoke the bundled Azure CLI Python runtime directly; Windows cannot
        # CreateProcess a .cmd file when shell=False.
        executable = Path(command).resolve().parent.parent / "python.exe"
        command_args = [str(executable), "-IBm", "azure.cli", *args]
    else:
        command_args = [command, *args]
    try:
        result = subprocess.run(
            command_args,
            capture_output=True,
            text=True,
            check=False,
            timeout=AZURE_CLI_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise SmokeFailure(
            f"Azure CLI command timed out after {AZURE_CLI_TIMEOUT_SECONDS}s; no event was sent."
        ) from error
    if result.returncode:
        raise SmokeFailure("Azure CLI command failed; details were withheld.")
    return result.stdout.strip()


def azure_arm_json(method: str, url: str, access_token: str) -> dict:
    """Call ARM directly; some Azure CLI WebApp commands stall in this lab."""
    request = Request(
        url,
        data=b"" if method == "POST" else None,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=AZURE_ARM_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        # Never include the request headers or response body (which may contain keys).
        raise SmokeFailure(f"Azure management request failed ({type(error).__name__}).") from None


def azure_json(url: str, key: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "x-functions-key": key})
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in {408, 425, 429, 500, 502, 503, 504}:
            raise AzureTransientReadError(
                f"Azure GET temporarily returned HTTP {error.code}."
            ) from None
        raise SmokeFailure(f"Azure GET returned HTTP {error.code}.") from None
    except (URLError, TimeoutError) as error:
        raise AzureTransientReadError(
            f"Azure GET temporarily failed ({type(error).__name__})."
        ) from None
    except json.JSONDecodeError:
        raise SmokeFailure("Azure GET returned invalid JSON.") from None


def azure_post(url: str, key: str, payload: dict) -> tuple[int, dict]:
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-functions-key": key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise SmokeFailure(f"Azure POST returned HTTP {error.code}.") from None
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"Azure POST failed ({type(error).__name__}).") from None


def require_http_status(
    url: str, payload: dict, expected_status: int, key: str | None = None
) -> None:
    """Assert an ingress response without logging its body or any key."""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if key:
        headers["x-functions-key"] = key
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            actual_status = response.status
    except HTTPError as error:
        actual_status = error.code
    except (URLError, TimeoutError) as error:
        raise SmokeFailure(
            f"Azure ingress probe failed ({type(error).__name__}); expected HTTP {expected_status}."
        ) from None
    if actual_status != expected_status:
        raise SmokeFailure(
            f"Azure ingress probe returned HTTP {actual_status}; expected {expected_status}."
        )


def verify_ingress_guards(base_url: str, key: str) -> None:
    """Check auth/source gates and ensure rejected probes were not persisted."""
    event_id = f"security-probe-{uuid.uuid4().hex}"
    payload = {
        "event_id": event_id,
        "event_type": "order.created",
        "source": "unauthorized-security-probe",
        "order": {
            "reference": "REJECTED-SECURITY-PROBE",
            "items": [{"sku": SKU, "quantity": 1}],
        },
    }
    url = f"{base_url}/api/fulfillment/events"
    require_http_status(url, payload, 401)
    require_http_status(url, payload, 400, key)
    status = azure_json(f"{base_url}/api/fulfillment/events/{event_id}", key)
    if status.get("status") != "pending":
        raise SmokeFailure("A rejected ingress probe unexpectedly created an event.")


def wait_for_result(base_url: str, key: str, event_id: str) -> dict:
    deadline = time.monotonic() + POLL_SECONDS
    last_transient_error: AzureTransientReadError | None = None
    while time.monotonic() < deadline:
        try:
            result = azure_json(
                f"{base_url}/api/fulfillment/events/{event_id}", key
            )
        except AzureTransientReadError as error:
            last_transient_error = error
        else:
            if result.get("status") != "pending":
                return result
        time.sleep(min(3, max(0, deadline - time.monotonic())))
    if last_transient_error:
        raise SmokeFailure(
            f"Event {event_id} remained unreadable after {POLL_SECONDS}s; "
            "inspect its status before retrying the test."
        ) from last_transient_error
    raise SmokeFailure(
        f"Event {event_id} remained pending after {POLL_SECONDS}s; it may still be processed, "
        "so inspect its status before retrying the test."
    )


def check_item_result(result: dict, expected_stock: int) -> None:
    if result.get("mode") != "demo-inventory-ledger":
        raise SmokeFailure("Azure did not identify the result as the demo ledger.")
    matching = [item for item in result.get("items", []) if item.get("sku") == SKU]
    if not matching or matching[0].get("on_hand_after") != expected_stock:
        raise SmokeFailure("Azure result did not report the expected demo stock.")


def current_demo_stock(base_url: str, key: str) -> int:
    inventory = azure_json(f"{base_url}/api/wms/inventory", key)
    if inventory.get("mode") != "demo-inventory-ledger" or inventory.get("is_real_erp") is not False:
        raise SmokeFailure("Refusing to reconcile against an inventory not marked as demo data.")
    product = next(
        (item for item in inventory.get("items", []) if item.get("sku") == SKU), None
    )
    if not product or not isinstance(product.get("on_hand"), int):
        raise SmokeFailure("The demo stock level is unavailable for reconciliation.")
    return product["on_hand"]


def require_empty_poison_queue(base_url: str, key: str, phase: str) -> None:
    """Check poison-queue metadata only; never read or delete queue messages."""
    status = azure_json(f"{base_url}/api/wms/poison-queue", key)
    count = status.get("approximate_message_count")
    if status.get("status") != "ok" or status.get("payloads_exposed") is not False:
        raise SmokeFailure(
            f"Poison-queue metadata is unavailable {phase}; no messages were read."
        )
    if type(count) is not int or count != 0:
        raise SmokeFailure(
            f"Poison queue is not empty {phase} (approximate count: {count}); "
            "no messages were read or changed."
        )


def sale_mutation_confirmed(
    base_url: str, key: str, event_id: str, baseline: int
) -> bool:
    """Return whether one demo unit was deducted; never guess during compensation."""
    event = azure_json(f"{base_url}/api/fulfillment/events/{event_id}", key)
    if event.get("status") == "pending":
        raise SmokeFailure(
            f"Sale event {event_id} is still pending; no compensation was sent. "
            "Inspect its status and stock before retrying the test."
        )
    stock = current_demo_stock(base_url, key)
    if stock == baseline - 1:
        return True
    if stock == baseline:
        return False
    raise SmokeFailure(
        f"Sale event {event_id} left stock at an unexpected level; "
        "no compensation was sent. Inspect the demo ledger before retrying."
    )


def main() -> int:
    if os.environ.get("TANGAMA_LIVE_AZURE_SMOKE") != OPT_IN_VALUE:
        print(
            "REFUSED: set TANGAMA_LIVE_AZURE_SMOKE=" + OPT_IN_VALUE +
            " to authorize this synthetic live test."
        )
        return 2

    account = json.loads(azure_cli("account", "show", "--output", "json"))
    if account.get("name") != "Azure for Students" or account.get("state") != "Enabled":
        raise SmokeFailure("The active Azure account is not the expected enabled student subscription.")

    access_token = json.loads(
        azure_cli(
            "account", "get-access-token", "--resource", "https://management.azure.com/",
            "--output", "json",
        )
    ).get("accessToken")
    if not access_token:
        raise SmokeFailure("Azure CLI did not return an ARM access token.")
    subscription_id = account.get("id")
    if not subscription_id:
        raise SmokeFailure("The active Azure subscription ID is unavailable.")
    site_resource = (
        f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/"
        f"{RESOURCE_GROUP}/providers/Microsoft.Web/sites/{FUNCTION_APP}"
    )
    function = azure_arm_json(
        "GET", f"{site_resource}?api-version=2023-12-01", access_token
    ).get("properties", {})
    host = function.get("host")
    if (
        function.get("state") != "Running"
        or function.get("httpsOnly") is not True
    ):
        raise SmokeFailure("The expected HTTPS-only Azure Function is not running.")
    host = function.get("defaultHostName")
    if not isinstance(host, str) or not host.endswith(".azurewebsites.net"):
        raise SmokeFailure("The expected Azure Function host name is unavailable.")

    # The secret stays in memory and is never written to a file or printed.
    host_keys = azure_arm_json(
        "POST",
        f"{site_resource}/host/default/listkeys?api-version=2023-12-01",
        access_token,
    )
    key = host_keys.get("functionKeys", {}).get("default")
    access_token = None
    if not isinstance(key, str) or not key:
        raise SmokeFailure("Azure did not return a usable Function key.")

    base_url = f"https://{host}"
    verify_ingress_guards(base_url, key)
    inventory = azure_json(f"{base_url}/api/wms/inventory", key)
    if inventory.get("mode") != "demo-inventory-ledger" or inventory.get("is_real_erp") is not False:
        raise SmokeFailure("Refusing to mutate an inventory not marked as fictional demo data.")
    product = next(
        (item for item in inventory.get("items", []) if item.get("sku") == SKU), None
    )
    if not product or not isinstance(product.get("on_hand"), int) or product["on_hand"] < 1:
        raise SmokeFailure("The selected demo SKU is missing or has no stock to sell.")
    baseline = product["on_hand"]
    require_empty_poison_queue(base_url, key, "before the synthetic test")

    restore_event_id: str | None = None
    sale_completed = False
    restored = False

    with tempfile.TemporaryDirectory(prefix="tangama-live-erp-smoke-") as temp_dir:
        admin_username = f"live-smoke-{uuid.uuid4().hex[:8]}@example.invalid"
        admin_password = secrets.token_urlsafe(24)
        local_database = str(Path(temp_dir) / "portal.sqlite3")
        os.environ.update(
            {
                "DATABASE_PATH": local_database,
                "DATABASE_URL": "",
                "AZURE_FULFILLMENT_URL": base_url,
                "AZURE_FUNCTION_KEY": key,
                "AUTO_DISPATCH_EVENTS": "true",
                "OUTBOX_RETRY_INTERVAL": "0",
                "VOICE_RECORDINGS_ENABLED": "false",
                "DB_SECRET_ARN": "",
                "BOOTSTRAP_ADMIN_USERNAME": admin_username,
                "BOOTSTRAP_ADMIN_PASSWORD": admin_password,
                "APP_SESSION_SECRET": secrets.token_urlsafe(32),
            }
        )
        release_path = ROOT / "app" / "aws_release" / "current"
        sys.path.insert(0, str(release_path))
        import importlib.util  # noqa: PLC0415

        module_spec = importlib.util.spec_from_file_location(
            "tangama_live_aws_release", release_path / "app.py"
        )
        if module_spec is None or module_spec.loader is None:
            raise SmokeFailure("Could not load the current AWS release artifact.")
        release_module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = release_module
        module_spec.loader.exec_module(release_module)
        portal = release_module.create_app(
            {
                "TESTING": True,
                "DATABASE_URL": "",
                "DATABASE_PATH": local_database,
                "AZURE_FULFILLMENT_URL": base_url,
                "AZURE_FUNCTION_KEY": key,
                "AUTO_DISPATCH_EVENTS": True,
                "OUTBOX_RETRY_INTERVAL": 0,
                "VOICE_RECORDINGS_ENABLED": False,
                "DB_SECRET_ARN": "",
                "BOOTSTRAP_ADMIN_USERNAME": admin_username,
                "BOOTSTRAP_ADMIN_PASSWORD": admin_password,
                "SECRET_KEY": secrets.token_urlsafe(32),
            }
        )
        client = portal.test_client()
        csrf = client.get("/api/auth/session").get_json()["csrf_token"]
        login = client.post(
            "/api/auth/login",
            json={"username": admin_username, "password": admin_password},
            headers={"X-CSRF-Token": csrf},
        )
        if login.status_code != 200:
            raise SmokeFailure("Temporary AWS-release ERP administrator login failed.")
        csrf = client.get("/api/auth/session").get_json()["csrf_token"]

        customer = client.post(
            "/api/erp/partners",
            json={"kind": "customer", "name": "QA live ERP customer"},
            headers={"X-CSRF-Token": csrf},
        )
        supplier = client.post(
            "/api/erp/partners",
            json={"kind": "supplier", "name": "QA live ERP supplier"},
            headers={"X-CSRF-Token": csrf},
        )
        if customer.status_code != 201 or supplier.status_code != 201:
            raise SmokeFailure("Could not create isolated temporary ERP partners.")

        sale = client.post(
            "/api/erp/sales/orders",
            json={
                "partner_id": customer.get_json()["id"],
                "items": [{"sku": SKU, "quantity": 1}],
            },
            headers={"X-CSRF-Token": csrf},
        )
        if sale.status_code != 201:
            raise SmokeFailure(f"ERP sale creation failed (HTTP {sale.status_code}).")
        sale_document = sale.get_json()
        sale_event_id = sale_document["event_id"]
        try:
            sale_result = wait_for_result(base_url, key, sale_event_id)
            if sale_result.get("status") != "demo_fulfillment_completed":
                raise SmokeFailure(f"ERP sale ended with status {sale_result.get('status')}.")
            sale_completed = True
            check_item_result(sale_result, baseline - 1)

            refreshed_sale = client.post(
                f"/api/erp/sales/orders/{sale_document['id']}/refresh",
                headers={"X-CSRF-Token": csrf},
            )
            if refreshed_sale.status_code != 200 or refreshed_sale.get_json().get("status") != "completed_demo":
                raise SmokeFailure("ERP did not reconcile the completed Azure sale.")

            purchase = client.post(
                "/api/erp/purchases/orders",
                json={
                    "partner_id": supplier.get_json()["id"],
                    "items": [{"sku": SKU, "quantity": 1}],
                },
                headers={"X-CSRF-Token": csrf},
            )
            if purchase.status_code != 201:
                raise SmokeFailure(f"ERP compensation purchase failed (HTTP {purchase.status_code}).")
            purchase_document = purchase.get_json()
            receipt = client.post(
                f"/api/erp/purchases/orders/{purchase_document['id']}/receive",
                headers={"X-CSRF-Token": csrf},
            )
            if receipt.status_code != 202:
                raise SmokeFailure("ERP did not enqueue the compensating demo receipt.")
            restore_event_id = receipt.get_json()["event_id"]
            restore_result = wait_for_result(base_url, key, restore_event_id)
            if restore_result.get("status") != "demo_restock_completed":
                raise SmokeFailure(f"Compensating receipt ended with status {restore_result.get('status')}.")
            check_item_result(restore_result, baseline)
            restored = True

            refreshed_purchase = client.post(
                f"/api/erp/purchases/orders/{purchase_document['id']}/refresh",
                headers={"X-CSRF-Token": csrf},
            )
            if refreshed_purchase.status_code != 200 or refreshed_purchase.get_json().get("status") != "received_demo":
                raise SmokeFailure("ERP did not reconcile the compensating receipt.")

            final_inventory = azure_json(f"{base_url}/api/wms/inventory", key)
            final_product = next(
                (item for item in final_inventory.get("items", []) if item.get("sku") == SKU), None
            )
            if not final_product or final_product.get("on_hand") != baseline:
                raise SmokeFailure("Final Azure demo stock does not match the captured baseline.")
            require_empty_poison_queue(base_url, key, "after the synthetic test")
        except Exception:
            if sale_event_id and not restored:
                try:
                    sale_completed = sale_mutation_confirmed(
                        base_url, key, sale_event_id, baseline
                    )
                    if not sale_completed:
                        restored = True
                        print("COMPENSATION=NOT_REQUIRED; demo stock remained at baseline")
                except Exception as sale_state_error:
                    print(
                        f"COMPENSATION=NOT_SENT; inspect synthetic sale event {sale_event_id} "
                        "and demo stock before retrying; "
                        f"reason={type(sale_state_error).__name__}",
                        file=sys.stderr,
                    )
                    raise SmokeFailure(
                        f"Sale event {sale_event_id} has no safely reconciled stock state; "
                        "no compensation was sent. Inspect the event and inventory before retrying."
                    ) from None
            if sale_completed and not restored:
                try:
                    if restore_event_id is None:
                        restore_event_id = f"evt-restore-{uuid.uuid4().hex}"
                        _, receipt_ack = azure_post(
                            f"{base_url}/api/fulfillment/events",
                            key,
                            {
                                "event_id": restore_event_id,
                                "event_type": "purchase.received",
                                "schema_version": "1.0",
                                "source": "tangamandapio-erp",
                                "occurred_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "purchase_order": {
                                    "reference": "QA-COMPENSATION",
                                    "items": [{"sku": SKU, "quantity": 1}],
                                },
                            },
                        )
                        if receipt_ack.get("status") not in {"queued", "queued_duplicate"}:
                            raise SmokeFailure("Azure did not accept the compensation event.")
                    compensation = wait_for_result(base_url, key, restore_event_id)
                    if compensation.get("status") != "demo_restock_completed":
                        raise SmokeFailure("Azure compensation did not complete.")
                    check_item_result(compensation, baseline)
                    restored = True
                except Exception as compensation_error:
                    print(
                        f"COMPENSATION=FAILED; inspect synthetic event {restore_event_id or sale_event_id}; "
                        f"reason={type(compensation_error).__name__}",
                        file=sys.stderr,
                    )
            raise

    print("SUBSCRIPTION=Azure for Students (Enabled)")
    print("FUNCTION=Running; HTTPS-only")
    print("INGRESS_GUARDS=unauthenticated_401; unauthorized_source_400; no event persisted")
    print("PORTAL=app/aws_release/current (local process; not the AWS instance)")
    print("FLOW=ERP sale -> durable outbox -> Azure Queue/Function -> ERP reconciliation")
    print(f"SALE_EVENT_ID={sale_event_id}")
    print(f"COMPENSATION_EVENT_ID={restore_event_id}")
    print("SALE=demo_fulfillment_completed; one demo unit deducted")
    print("COMPENSATION=demo_restock_completed; demo stock restored to baseline")
    print("LIVE_E2E=PASSED; synthetic event records remain in Azure audit storage")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as error:
        print(f"LIVE_E2E=FAILED; {error}", file=sys.stderr)
        raise SystemExit(1)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"LIVE_E2E=FAILED; {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
