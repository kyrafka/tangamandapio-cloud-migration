#!/usr/bin/env python3
"""Read-only preflight for the proposed AWS–Azure Tailscale overlay."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import shutil
import subprocess
import sys
from typing import Any


def _run_json(command: list[str]) -> tuple[bool, Any]:
    """Run a read-only CLI command without ever surfacing its raw output."""
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False, None
    if result.returncode != 0:
        return False, None
    try:
        return True, json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return False, None


def _network_pair_is_valid(aws_cidr: str, azure_cidr: str) -> bool:
    try:
        aws_network = ipaddress.ip_network(aws_cidr, strict=True)
        azure_network = ipaddress.ip_network(azure_cidr, strict=True)
    except ValueError:
        return False
    return aws_network.version == azure_network.version and not aws_network.overlaps(azure_network)


def evaluate(
    *,
    aws_region: str = "us-east-1",
    aws_cidr: str = "10.10.0.0/16",
    azure_resource_group: str = "rg-tangama-private-network",
    azure_vnet_name: str = "vnet-tangama-private",
    azure_cidr: str = "10.20.0.0/16",
) -> dict[str, Any]:
    available = {name: shutil.which(name) for name in ("tailscale", "aws", "az")}
    checks: dict[str, Any] = {
        "tailscale_cli": bool(available["tailscale"]),
        "aws_cli": bool(available["aws"]),
        "azure_cli": bool(available["az"]),
        "tailscale_connected": False,
        "aws_authenticated": False,
        "aws_vpc_present": False,
        "azure_authenticated": False,
        "azure_vnet_present": False,
        "cidrs_non_overlapping": _network_pair_is_valid(aws_cidr, azure_cidr),
        "ephemeral_auth_key_present": bool(os.environ.get("TAILSCALE_AUTH_KEY")),
    }
    blockers: list[str] = []

    if checks["tailscale_cli"]:
        ok, status = _run_json([available["tailscale"], "status", "--json"])
        checks["tailscale_connected"] = bool(
            ok
            and isinstance(status, dict)
            and status.get("BackendState") == "Running"
            and isinstance(status.get("Self"), dict)
            and status["Self"].get("Online") is True
        )

    if checks["aws_cli"]:
        ok, identity = _run_json(
            [available["aws"], "sts", "get-caller-identity", "--output", "json"]
        )
        checks["aws_authenticated"] = bool(ok and isinstance(identity, dict) and identity.get("Account"))
        if checks["aws_authenticated"]:
            ok, inventory = _run_json(
                [available["aws"], "ec2", "describe-vpcs", "--region", aws_region, "--output", "json"]
            )
            if ok and isinstance(inventory, dict):
                matches = [
                    vpc
                    for vpc in inventory.get("Vpcs", [])
                    if isinstance(vpc, dict)
                    and vpc.get("CidrBlock") == aws_cidr
                    and vpc.get("State") == "available"
                ]
                checks["aws_vpc_present"] = len(matches) == 1

    if checks["azure_cli"]:
        ok, account = _run_json([available["az"], "account", "show", "--output", "json"])
        checks["azure_authenticated"] = bool(ok and isinstance(account, dict) and account.get("id"))
        if checks["azure_authenticated"]:
            ok, inventory = _run_json([available["az"], "network", "vnet", "list", "--output", "json"])
            if ok and isinstance(inventory, list):
                matches = []
                for vnet in inventory:
                    if not isinstance(vnet, dict):
                        continue
                    if vnet.get("name", "").casefold() != azure_vnet_name.casefold():
                        continue
                    if vnet.get("resourceGroup", "").casefold() != azure_resource_group.casefold():
                        continue
                    prefixes = (vnet.get("addressSpace") or {}).get("addressPrefixes", [])
                    if azure_cidr in prefixes:
                        matches.append(vnet)
                checks["azure_vnet_present"] = len(matches) == 1

    required = (
        "tailscale_cli",
        "aws_cli",
        "azure_cli",
        "tailscale_connected",
        "aws_authenticated",
        "aws_vpc_present",
        "azure_authenticated",
        "azure_vnet_present",
        "cidrs_non_overlapping",
        "ephemeral_auth_key_present",
    )
    labels = {
        "tailscale_cli": "No se encontró el cliente Tailscale.",
        "aws_cli": "No se encontró AWS CLI.",
        "azure_cli": "No se encontró Azure CLI.",
        "tailscale_connected": "El equipo local no está conectado al tailnet Tailscale.",
        "aws_authenticated": "AWS CLI no pudo validar una sesión activa.",
        "aws_vpc_present": f"No se encontró exactamente una VPC disponible con CIDR {aws_cidr}.",
        "azure_authenticated": "Azure CLI no pudo validar una suscripción activa.",
        "azure_vnet_present": (
            f"No se encontró exactamente una VNet {azure_vnet_name} en "
            f"{azure_resource_group} con CIDR {azure_cidr}."
        ),
        "cidrs_non_overlapping": "Los CIDR propuestos son inválidos o se solapan.",
        "ephemeral_auth_key_present": "Falta TAILSCALE_AUTH_KEY; no se almacena ni se imprime su valor.",
    }
    blockers.extend(labels[key] for key in required if not checks[key])
    return {
        "result": "READY_FOR_MANUAL_REVIEW" if not blockers else "BLOCKED",
        "read_only": True,
        "checks": checks,
        "blockers": blockers,
        "limits": [
            "No verifica permisos de creación ni aprueba rutas/ACL del tailnet.",
            "No crea recursos, cambia rutas ni registra dispositivos.",
            "Una clave presente solo se detecta como booleano; su validez no se comprueba.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument("--aws-cidr", default="10.10.0.0/16")
    parser.add_argument("--azure-resource-group", default="rg-tangama-private-network")
    parser.add_argument("--azure-vnet-name", default="vnet-tangama-private")
    parser.add_argument("--azure-cidr", default="10.20.0.0/16")
    args = parser.parse_args()
    report = evaluate(
        aws_region=args.aws_region,
        aws_cidr=args.aws_cidr,
        azure_resource_group=args.azure_resource_group,
        azure_vnet_name=args.azure_vnet_name,
        azure_cidr=args.azure_cidr,
    )
    # ASCII escaping keeps the JSON printable under legacy Windows console codepages.
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["result"] == "READY_FOR_MANUAL_REVIEW" else 2


if __name__ == "__main__":
    sys.exit(main())
