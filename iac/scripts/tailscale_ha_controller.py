#!/usr/bin/env python3
"""Fail-closed active/standby route controller for the AWS Tailscale pair."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def decide(state, route, primary, backup, failover_checks=3, failback_checks=10):
    """Return guarded counters and an optional route action."""
    if primary not in {"healthy", "unhealthy", "unknown"}:
        raise ValueError("invalid primary health")
    if backup not in {"healthy", "unhealthy", "unknown"}:
        raise ValueError("invalid backup health")
    if route not in {"primary", "backup", "other"}:
        raise ValueError("invalid route owner")
    current = {
        "primary_failures": max(0, int(state.get("primary_failures", 0))),
        "primary_recoveries": max(0, int(state.get("primary_recoveries", 0))),
    }
    if route == "other":
        return {"primary_failures": 0, "primary_recoveries": 0}, None
    if route == "primary":
        current["primary_recoveries"] = 0
        if primary == "healthy":
            current["primary_failures"] = 0
            return current, None
        if primary == "unknown":
            current["primary_failures"] = 0
            return current, None
        current["primary_failures"] = min(current["primary_failures"] + 1, failover_checks)
        if current["primary_failures"] >= failover_checks and backup == "healthy":
            return current, "switch_to_backup"
        return current, None

    current["primary_failures"] = 0
    if backup != "healthy":
        current["primary_recoveries"] = 0
        if primary == "healthy":
            return current, "switch_to_primary"
        return current, None
    if primary != "healthy":
        current["primary_recoveries"] = 0
        return current, None
    current["primary_recoveries"] = min(current["primary_recoveries"] + 1, failback_checks)
    if current["primary_recoveries"] >= failback_checks:
        return current, "switch_to_primary"
    return current, None


@dataclass(frozen=True)
class Config:
    region: str
    route_table_id: str
    destination: str
    primary_eni: str
    backup_eni: str
    primary_private_ip: str
    hostname: str
    sns_topic_arn: str = ""

    def __post_init__(self):
        if not re.fullmatch(r"us-[a-z]+-\d", self.region):
            raise ValueError("invalid region")
        if not re.fullmatch(r"rtb-[0-9a-f]{8,17}", self.route_table_id):
            raise ValueError("invalid route table")
        network = ipaddress.ip_network(self.destination, strict=True)
        if network.version != 4 or network.prefixlen != 32 or str(network) != "10.20.1.4/32":
            raise ValueError("destination must be the validated private endpoint 10.20.1.4/32")
        if not re.fullmatch(r"eni-[0-9a-f]{8,17}", self.primary_eni):
            raise ValueError("invalid primary interface")
        if not re.fullmatch(r"eni-[0-9a-f]{8,17}", self.backup_eni):
            raise ValueError("invalid backup interface")
        if self.primary_eni == self.backup_eni:
            raise ValueError("router interfaces must be different")
        primary_ip = ipaddress.ip_address(self.primary_private_ip)
        if primary_ip.version != 4 or not primary_ip.is_private:
            raise ValueError("primary private IP must be private IPv4")
        if not re.fullmatch(r"[a-z0-9-]+\.azurewebsites\.net", self.hostname):
            raise ValueError("invalid Azure hostname")
        if self.sns_topic_arn and not re.fullmatch(
            r"arn:aws(?:-cn|-us-gov)?:sns:[a-z0-9-]+:\d{12}:[A-Za-z0-9_-]+", self.sns_topic_arn
        ):
            raise ValueError("invalid SNS topic ARN")


def classify_route(table, destination, primary_eni, backup_eni):
    """Accept only a single route whose target is one of the two known ENIs."""
    matches = [route for route in table.get("Routes", [])
               if route.get("DestinationCidrBlock") == destination]
    if len(matches) != 1 or matches[0].get("State") not in {"active", "blackhole"}:
        return "other"
    target = matches[0].get("NetworkInterfaceId")
    if target == primary_eni:
        return "primary"
    if target == backup_eni:
        return "backup"
    return "other"


def probe(url, timeout=0.8):
    try:
        with urlopen(url, timeout=timeout) as response:
            return "healthy" if response.status == 200 else "unhealthy"
    except HTTPError as error:
        return "unhealthy" if error.code else "unknown"
    except (URLError, TimeoutError, OSError):
        return "unhealthy"


def probe_health_pair(primary_probe, backup_probe):
    """Probe both routers together so a slow peer does not double each poll."""
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="router-health") as pool:
        primary_future = pool.submit(primary_probe)
        backup_future = pool.submit(backup_probe)
        return primary_future.result(), backup_future.result()


class AWSRouteControl:
    def __init__(self, config: Config, ec2, sns, verify_timeout=2.0):
        self.config = config
        self.ec2 = ec2
        self.sns = sns
        self.verify_timeout = verify_timeout
        self.last_route = "other"
        self.read_route_after = 0.0

    def current_route(self, *, cached=False):
        if cached and time.monotonic() < self.read_route_after:
            return self.last_route
        data = self.ec2.describe_route_tables(RouteTableIds=[self.config.route_table_id])
        tables = data.get("RouteTables", [])
        self.last_route = classify_route(tables[0], self.config.destination, self.config.primary_eni,
                                         self.config.backup_eni) if len(tables) == 1 else "other"
        self.read_route_after = time.monotonic() + 3.0
        return self.last_route

    def primary_health(self):
        return probe(f"http://{self.config.primary_private_ip}:9797/route-health")

    def backup_health(self):
        return probe("http://127.0.0.1:9797/route-health")

    def switch(self, target):
        if target not in {"primary", "backup"}:
            raise ValueError("route target must be a known router")
        address = "127.0.0.1" if target == "backup" else self.config.primary_private_ip
        interface = self.config.backup_eni if target == "backup" else self.config.primary_eni
        if probe(f"http://{address}:9797/health", timeout=2.4) != "healthy":
            raise RuntimeError("target did not pass a fresh HTTPS check")
        expected = "primary" if target == "backup" else "backup"
        if self.current_route() != expected:
            raise RuntimeError("route changed or is unknown; refusing to overwrite it")
        self.ec2.replace_route(RouteTableId=self.config.route_table_id,
                               DestinationCidrBlock=self.config.destination, NetworkInterfaceId=interface)
        self.read_route_after = 0.0
        deadline = time.monotonic() + self.verify_timeout
        while time.monotonic() < deadline:
            if self.current_route() == target:
                return
            time.sleep(0.1)
        raise RuntimeError("route replacement was not observed before the verification deadline")

    def publish(self, target):
        if not self.config.sns_topic_arn:
            return
        message = {
            "project": "Tangamandapio",
            "event": "private_wms_router_route_changed",
            "route_owner": target,
            "destination": self.config.destination,
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        self.sns.publish(TopicArn=self.config.sns_topic_arn, Subject="Conmutación de la ruta privada WMS",
                         Message=json.dumps(message, ensure_ascii=False))


def run_once(cloud: AWSRouteControl, state, sdk_errors=()):
    observation_errors = (OSError, RuntimeError) + sdk_errors
    try:
        route = cloud.current_route(cached=True)
        primary, backup = probe_health_pair(cloud.primary_health, cloud.backup_health)
        new_state, action = decide(state, route, primary, backup)
        if action:
            target = "backup" if action == "switch_to_backup" else "primary"
            cloud.switch(target)
        return new_state, {
            "route_before": route,
            "primary_health": primary,
            "backup_health": backup,
            "action": action,
            "route_after": target if action else route,
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    except observation_errors as error:
        return {"primary_failures": 0, "primary_recoveries": 0}, {
            "action": "observation_error",
            "error_type": type(error).__name__,
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        }


def write_state(path, state):
    target = Path(path)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(state), encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("region", "route-table-id", "destination", "primary-eni", "backup-eni",
                 "primary-private-ip", "hostname"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--sns-topic-arn", default="")
    parser.add_argument("--state-file", default="/var/lib/tangamandapio/route-ha/state.json")
    parser.add_argument("--interval", type=float)
    args = parser.parse_args()
    try:
        config = Config(args.region, args.route_table_id, args.destination, args.primary_eni,
                        args.backup_eni, args.primary_private_ip, args.hostname, args.sns_topic_arn)
        try:
            state = json.loads(Path(args.state_file).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            state = {"primary_failures": 0, "primary_recoveries": 0}
        if args.interval is not None and args.interval < 0.3:
            raise ValueError("polling interval must be at least 0.3 seconds")
        from botocore.config import Config as SDKConfig
        from botocore.exceptions import BotoCoreError, ClientError
        from botocore.session import get_session

        errors = (BotoCoreError, ClientError)
        session = get_session()
        sdk_config = SDKConfig(connect_timeout=2, read_timeout=2, retries={"total_max_attempts": 1})
        ec2 = session.create_client("ec2", region_name=config.region, config=sdk_config)
        sns = session.create_client("sns", region_name=config.region, config=sdk_config)
        cloud = AWSRouteControl(config, ec2, sns)
        previous_observation = None
        while True:
            new_state, result = run_once(cloud, state, errors)
            if state != new_state or previous_observation is None:
                write_state(args.state_file, new_state)
            state = new_state
            observation = {key: value for key, value in result.items() if key != "observed_at_utc"}
            if previous_observation != observation or args.interval is None:
                print(json.dumps({**state, **result}, ensure_ascii=False), flush=True)
                previous_observation = observation
            if result.get("action") in {"switch_to_backup", "switch_to_primary"}:
                try:
                    cloud.publish(result["route_after"])
                except errors as error:
                    print(json.dumps({"action": "sns_publish_error", "error_type": type(error).__name__}), flush=True)
            if args.interval is None:
                return 0 if result.get("action") != "observation_error" else 1
            time.sleep(args.interval)
    except ValueError as error:
        print(json.dumps({"action": "invalid_configuration", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
