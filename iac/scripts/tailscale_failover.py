"""Conservative, one-way route failover for the private WMS pilot."""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import time


def decide(failures, primary, backup, route):
    """Return (consecutive confirmed failures, switch_to_backup)."""
    if primary not in {"healthy", "unhealthy", "unknown"}:
        raise ValueError("invalid primary health")
    if backup not in {"healthy", "unhealthy", "unknown"}:
        raise ValueError("invalid backup health")
    if route not in {"primary", "backup", "other"}:
        raise ValueError("invalid route owner")
    if route != "primary" or primary != "unhealthy":
        return 0, False
    failures = min(max(0, int(failures)) + 1, 3)
    return failures, failures >= 3 and backup == "healthy"


def run_cycle(cloud, failures):
    """Run one guarded observation and, when justified, change the route once."""
    try:
        route = cloud.current_route()
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError, OSError):
        return 0, False
    if route != "primary":
        return 0, False
    primary = cloud.primary_health()
    backup = cloud.backup_health() if primary == "unhealthy" else "unknown"
    failures, switch = decide(failures, primary, backup, route)
    if switch:
        cloud.switch_to_backup()
    return failures, switch


def run_ha_cycle(cloud, state, prefer_self=False):
    """Take over a failed peer; optionally return to this preferred router.

    The active peer is named ``primary`` by AWSCloud; ``backup`` is the local
    router. The preferred instance requires ten healthy observations before
    taking traffic back from a healthy peer, to prevent rapid flapping.
    """
    clean = {"failures": 0, "recoveries": 0}
    try:
        if cloud.current_route() != "primary":
            return clean, None
        peer = cloud.primary_health()
        if peer not in {"healthy", "unhealthy", "unknown"}:
            return clean, None
        if peer == "unknown":
            return clean, None
        if peer == "unhealthy":
            failures = min(max(0, int(state.get("failures", 0))) + 1, 3)
            next_state = {"failures": failures, "recoveries": 0}
            if failures == 3 and cloud.backup_health() == "healthy":
                cloud.switch_to_backup()
                return next_state, "peer_failure"
            return next_state, None
        if not prefer_self or cloud.backup_health() != "healthy":
            return clean, None
        recoveries = min(max(0, int(state.get("recoveries", 0))) + 1, 10)
        next_state = {"failures": 0, "recoveries": recoveries}
        if recoveries == 10:
            cloud.switch_to_backup()
            return next_state, "preferred_recovery"
        return next_state, None
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError, OSError, RuntimeError):
        return clean, None


def classify_route(table, destination, primary_eni, backup_eni):
    """Refuse missing, duplicate, inactive or unexpected route targets."""
    matches = [item for item in table.get("Routes", []) if item.get("DestinationCidrBlock") == destination]
    if len(matches) != 1 or matches[0].get("State") != "active":
        return "other"
    interface = matches[0].get("NetworkInterfaceId")
    if interface == primary_eni:
        return "primary"
    if interface == backup_eni:
        return "backup"
    return "other"


def parse_remote_health(status, output):
    """SSM failure or ambiguous output is not proof of a router failure."""
    if status != "Success":
        return "unknown"
    return {"HEALTHY": "healthy", "UNHEALTHY": "unhealthy"}.get(output.strip(), "unknown")


def parse_aws_json(output):
    """Some successful AWS mutations return no JSON body."""
    return json.loads(output) if output.strip() else {}


class AWSCloud:
    """Inspect one primary router from the backup using SSM and AWS CLI."""

    def __init__(self, region, table, destination, primary_instance, primary_eni, backup_eni, hostname):
        if not re.fullmatch(r"[a-z0-9-]+\.azurewebsites\.net", hostname):
            raise ValueError("invalid WMS hostname")
        if not re.fullmatch(r"[a-z0-9-]+", region):
            raise ValueError("invalid region")
        if not re.fullmatch(r"rtb-[0-9a-f]+", table):
            raise ValueError("invalid route table")
        if not re.fullmatch(r"i-[0-9a-f]+", primary_instance):
            raise ValueError("invalid instance")
        if not all(re.fullmatch(r"eni-[0-9a-f]+", value) for value in (primary_eni, backup_eni)):
            raise ValueError("invalid interface")
        network = ipaddress.ip_network(destination, strict=True)
        if network.version != 4 or network.prefixlen != 32 or not network.is_private:
            raise ValueError("destination must be one private IPv4 address")
        self.region, self.table, self.destination = region, table, destination
        self.primary_instance, self.primary_eni, self.backup_eni = primary_instance, primary_eni, backup_eni
        self.hostname, self.ip = hostname, str(network.network_address)

    def aws(self, *args):
        result = subprocess.run(["aws", "--region", self.region, *args, "--output", "json"],
                                capture_output=True, text=True, timeout=20, check=True)
        return parse_aws_json(result.stdout)

    def current_route(self):
        response = self.aws("ec2", "describe-route-tables", "--route-table-ids", self.table)
        tables = response.get("RouteTables", [])
        return classify_route(tables[0], self.destination, self.primary_eni, self.backup_eni) if len(tables) == 1 else "other"

    def health_command(self):
        # The CIDR and host are deliberately fixed to the existing app subnets
        # and a validated WMS IP; the probe never contains credentials.
        return (
            "if [ \"$(sysctl -n net.ipv4.ip_forward)\" = 1 ] && "
            "iptables -t nat -C POSTROUTING -s 10.10.10.0/23 -d " + self.destination +
            " -p tcp --dport 443 -o tailscale0 -j MASQUERADE >/dev/null 2>&1 && "
            "[ \"$(curl -sS --connect-timeout 5 --max-time 10 --resolve " + self.hostname + ":443:" + self.ip +
            " -o /dev/null -w '%{http_code}' https://" + self.hostname + "/api/health 2>/dev/null)\" = 200 ]; "
            "then echo HEALTHY; else echo UNHEALTHY; fi"
        )

    def primary_health(self):
        try:
            data = self.aws("ec2", "describe-instances", "--instance-ids", self.primary_instance)
            state = data["Reservations"][0]["Instances"][0]["State"]["Name"]
            if state in {"stopped", "stopping", "terminated", "shutting-down"}:
                return "unhealthy"
            if state != "running":
                return "unknown"
            command = self.aws("ssm", "send-command", "--instance-ids", self.primary_instance,
                               "--document-name", "AWS-RunShellScript", "--parameters",
                               json.dumps({"commands": [self.health_command()]}))
            command_id = command["Command"]["CommandId"]
            for _ in range(10):
                time.sleep(2)
                try:
                    result = self.aws("ssm", "get-command-invocation", "--command-id", command_id,
                                      "--instance-id", self.primary_instance)
                except (subprocess.SubprocessError, json.JSONDecodeError):
                    continue
                if result.get("Status") in {"Success", "Failed", "TimedOut", "Cancelled"}:
                    return parse_remote_health(result.get("Status"), result.get("StandardOutputContent", ""))
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError, OSError):
            pass
        return "unknown"

    def backup_health(self):
        try:
            result = subprocess.run(["/bin/sh", "-c", self.health_command()], capture_output=True,
                                    text=True, timeout=20, check=True)
            return parse_remote_health("Success", result.stdout)
        except (subprocess.SubprocessError, OSError):
            return "unknown"

    def switch_to_backup(self):
        # Recheck the route immediately before writing; never replace an
        # unrelated or already-switched route.
        if self.current_route() != "primary":
            raise RuntimeError("route changed during observation")
        self.aws("ec2", "replace-route", "--route-table-id", self.table,
                 "--destination-cidr-block", self.destination, "--network-interface-id", self.backup_eni)


def render_systemd_service(cloud, prefer_self=False):
    """Render a unit only from validated cloud identifiers, without credentials."""
    return (
        "[Unit]\nDescription=Tangamandapio private WMS route failover monitor\n"
        "After=network-online.target tailscaled.service tangamandapio-wms-nat.service\n"
        "Wants=network-online.target\n[Service]\nType=oneshot\n"
        "ExecStart=/usr/bin/flock -n /run/tangamandapio-route-failover.lock "
        "/usr/bin/python3 /opt/tangamandapio/tailscale_failover.py "
        f"--region {cloud.region} --table {cloud.table} --destination {cloud.destination} "
        f"--primary-instance {cloud.primary_instance} --primary-eni {cloud.primary_eni} "
        f"--backup-eni {cloud.backup_eni} --hostname {cloud.hostname} "
        "--state-file /var/lib/tangamandapio-route-failover/state.json"
        + (" --prefer-self" if prefer_self else "") + "\nTimeoutStartSec=120\n"
    )


def installation_preflight(cloud):
    """Do not install automatic route control unless both paths are ready."""
    return (cloud.current_route() in {"primary", "backup"} and cloud.primary_health() == "healthy"
            and cloud.backup_health() == "healthy")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("region", "table", "destination", "primary-instance", "primary-eni", "backup-eni", "hostname"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--state-file", default="/var/lib/tangamandapio-route-failover/state.json")
    parser.add_argument("--render-service", action="store_true", help="print a unit without contacting AWS")
    parser.add_argument("--preflight", action="store_true", help="check both routers without changing routes")
    parser.add_argument("--prefer-self", action="store_true", help="return to this router after sustained healthy checks")
    args = parser.parse_args()
    state_path = Path(args.state_file)
    try:
        try:
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            state = {"failures": int(saved.get("failures", 0)), "recoveries": int(saved.get("recoveries", 0))}
        except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
            state = {"failures": 0, "recoveries": 0}
        cloud = AWSCloud(args.region, args.table, args.destination, args.primary_instance,
                         args.primary_eni, args.backup_eni, args.hostname)
        if args.render_service:
            print(render_systemd_service(cloud, args.prefer_self), end="")
            return 0
        if args.preflight:
            ready = installation_preflight(cloud)
            print(json.dumps({"ready": ready}))
            return 0 if ready else 2
        state, reason = run_ha_cycle(cloud, state, args.prefer_self)
        state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state), encoding="utf-8")
        os.replace(temporary, state_path)
        print(json.dumps({**state, "switched_to_backup": reason is not None, "reason": reason}))
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError):
        # Never convert an API/authentication/observation failure to unhealthy.
        print(json.dumps({"result": "observation_or_route_error"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
