"""Authenticated operational read endpoints for the portal and administration consoles."""

from datetime import date, datetime, time, timedelta, timezone
import json
import socket
from urllib.request import Request, urlopen

from flask import jsonify, request

from admin_cloud_tools import technical_test_results
from cloud_observability import collect_cloudwatch_metrics


LIMA = timezone(timedelta(hours=-5))


def history_range(start, end):
    """Convert inclusive calendar dates in Lima to a half-open UTC interval."""
    if start is None and end is None:
        return None
    if not start or not end or len(start) != 10 or len(end) != 10:
        raise ValueError("invalid_history_range")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first.isoformat() != start or last.isoformat() != end:
        raise ValueError("invalid_history_range")
    if not first <= last <= datetime.now(LIMA).date() or (last - first).days >= 31:
        raise ValueError("invalid_history_range")
    midnight = datetime.combine(first, time.min, LIMA)
    days = (last - first).days + 1
    return midnight.astimezone(timezone.utc), (midnight + timedelta(days=days)).astimezone(timezone.utc)


def _queue_health(service_url, key, inventory_url):
    queue = {"status": "unavailable", "pending": None, "poison": None}
    if not service_url or not key:
        return queue

    try:
        upstream = Request(
            inventory_url(service_url).removesuffix("inventory") + "queue-status",
            headers={"Accept": "application/json", "x-functions-key": key},
        )
        with urlopen(upstream, timeout=3) as response:
            counts = json.load(response)
    except (OSError, ValueError):
        return queue
    if not isinstance(counts, dict):
        return queue

    for name in ("pending", "poison"):
        count = counts.get(name)
        if type(count) is int and count >= 0:
            queue[name] = count
    available = sum(queue[name] is not None for name in ("pending", "poison"))
    queue["status"] = ("unavailable", "degraded", "ok")[available]
    return queue


def register_platform_routes(app, database_path, *, connect, require_roles, azure_inventory_url, database_kind):
    """Register the operational endpoints with the same role checks as the host portal."""

    @app.get("/api/platform/fulfillment-health")
    @require_roles("admin", "operations")
    def platform_fulfillment_health():
        with connect(database_path) as connection:
            counts = connection.execute(
                "SELECT COUNT(*) AS pending, MIN(created_at) AS oldest, "
                "COUNT(CASE WHEN attempts >= ? THEN 1 END) AS exhausted FROM outbox_events WHERE status != 'delivered'",
                (app.config["OUTBOX_RETRY_MAX_ATTEMPTS"],),
            ).fetchone()
        queue = _queue_health(
            app.config["AZURE_FULFILLMENT_URL"],
            app.config["AZURE_FUNCTION_KEY"],
            azure_inventory_url,
        )
        return jsonify(
            outbox=dict(counts),
            azure_queue=queue,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

    @app.get("/api/platform/overview")
    @require_roles("admin", "operations")
    def platform_overview():
        try:
            window_minutes = int(request.args.get("window", "60"))
        except (TypeError, ValueError):
            return jsonify(error="invalid_metrics_window"), 400
        start, end = request.args.get("from"), request.args.get("to")
        try:
            dates = history_range(start, end)
        except ValueError:
            return jsonify(error="invalid_history_range"), 400
        try:
            cloudwatch = collect_cloudwatch_metrics(app.config, window_minutes, history=dates)
        except ValueError:
            return jsonify(error="invalid_metrics_window"), 400
        if dates:
            cloudwatch["history"] = {"from": start, "to": end}
        return jsonify(
            cloudwatch=cloudwatch,
            application={
                "instance": socket.gethostname(),
                "requests_since_worker_start": app.extensions["metrics"]["requests_total"],
                "orders_created_since_worker_start": app.extensions["metrics"]["orders_created_total"],
                "counter_scope": "este proceso web; CloudWatch ALB agrega el tráfico de la capa",
            },
            security={
                "role_enforcement": "backend",
                "csrf": "enabled",
                "session_cookie_secure": bool(app.config["SESSION_COOKIE_SECURE"]),
                "session_cookie_httponly": bool(app.config["SESSION_COOKIE_HTTPONLY"]),
                "recordings_enabled": bool(app.config["VOICE_RECORDINGS_ENABLED"]),
                "waf_enabled": bool(
                    app.config.get("CLOUDWATCH_WAF_WEB_ACL_NAME")
                    and app.config.get("CLOUDWATCH_WAF_REGION")
                ),
                "database": database_kind(),
            },
        )

    @app.get("/api/admin/technical-tests")
    @require_roles("admin")
    def admin_technical_tests():
        try:
            evidence = technical_test_results()
        except (OSError, ValueError) as error:
            app.logger.warning("Technical test evidence unavailable (%s)", type(error).__name__)
            return jsonify(error="technical_tests_unavailable"), 503
        return jsonify(evidence), 200, {"Cache-Control": "no-store"}
