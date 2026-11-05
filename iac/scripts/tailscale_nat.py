#!/usr/bin/env python3
"""Render the narrowly scoped NAT service used by the AWS VPN routers.

The CLI renders a unit for review. The install function is called only by the
router installer after it verifies account, interface ownership, and project
tags; neither mode changes cloud security groups or enrolls the router.
"""
import argparse
import ipaddress
import os
from pathlib import Path
import subprocess
import sys


def render_service(source, destination):
    try:
        subnet = ipaddress.ip_network(source, strict=True)
        host = ipaddress.ip_address(destination)
    except ValueError:
        raise ValueError('Invalid source CIDR or destination IP') from None
    project_source = ipaddress.ip_network('10.10.10.0/23')
    project_destination = ipaddress.ip_network('10.20.1.0/24')
    if (subnet.version != 4 or not subnet.subnet_of(project_source) or
            host.version != 4 or host not in project_destination or
            host in (project_destination.network_address, project_destination.broadcast_address)):
        raise ValueError('NAT must remain within the project application and WMS networks')
    rule = f'-s {subnet} -d {host}/32 -p tcp --dport 443 -o tailscale0 -j MASQUERADE'
    return f'''[Unit]
Description=Tangamandapio WMS VPN scoped return NAT
After=network-online.target tailscaled.service
Wants=network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c '/usr/sbin/iptables -t nat -C POSTROUTING {rule} 2>/dev/null || /usr/sbin/iptables -t nat -A POSTROUTING {rule}'
[Install]
WantedBy=multi-user.target
'''


def install(source, destination, unit_path, sysctl_path):
    """Install only matching project files after the caller verifies identity."""
    unit_path, sysctl_path = Path(unit_path), Path(sysctl_path)
    contents = ((unit_path, render_service(source, destination)),
                (sysctl_path, 'net.ipv4.ip_forward=1\n'))
    # Validate all existing files before creating or changing anything.
    for path, value in contents:
        if path.is_symlink() or (path.exists() and (not path.is_file() or path.read_text(encoding='utf8') != value)):
            raise ValueError(f'Existing configuration conflicts: {path.name}')
    for path, value in contents:
        if not path.exists():
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
            fd = os.open(path, flags, 0o644)
            with os.fdopen(fd, 'w', encoding='utf8', newline='\n') as target:
                target.write(value)
    subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True, capture_output=True, text=True)
    subprocess.run(['systemctl', 'daemon-reload'], check=True, capture_output=True, text=True)
    subprocess.run(['systemctl', 'enable', '--now', 'tangamandapio-wms-nat.service'], check=True, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    try:
        print(render_service(args.source, args.destination), end='')
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
