#!/usr/bin/env python3
"""Verify or create the project WMS /32 route; never replace an existing route."""
import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys


def tags(resource):
    return {t.get('Key'): t.get('Value') for t in resource.get('Tags', [])}


def assess_route(table, vpc, stack, eni, destination):
    host = ipaddress.ip_address(destination)
    if host.version != 4 or host not in ipaddress.ip_network('10.20.1.0/24') or host in (ipaddress.ip_address('10.20.1.0'), ipaddress.ip_address('10.20.1.255')):
        raise ValueError('Destination is outside the project WMS subnet')
    t = tags(table)
    if table.get('VpcId') != vpc or t.get('aws:cloudformation:stack-name') != stack or t.get('aws:cloudformation:logical-id') != 'AppRouteTable':
        raise ValueError('Route table is not the project application table')
    routes = [r for r in table.get('Routes', []) if r.get('DestinationCidrBlock') == f'{host}/32']
    if not routes:
        return 'create'
    if len(routes) == 1 and routes[0].get('NetworkInterfaceId') == eni and routes[0].get('State') == 'active':
        return 'unchanged'
    raise ValueError('An existing route has a different or unhealthy target; no replacement allowed')


def validate_router(instance, interface, vpc, eni):
    t = tags(instance)
    if (instance.get('VpcId') != vpc or instance.get('State', {}).get('Name') != 'running' or
            t.get('Project') != 'Tangamandapio' or
            t.get('aws:cloudformation:stack-name') not in {'tangamandapio-tailscale-pilot', 'tangamandapio-tailscale-pilot-b'} or
            interface.get('VpcId') != vpc or interface.get('NetworkInterfaceId') != eni or
            interface.get('SourceDestCheck') is not False or
            interface.get('Attachment', {}).get('InstanceId') != instance.get('InstanceId')):
        raise ValueError('Router identity, state, VPC or forwarding is not verified')


def aws(*args):
    result = subprocess.run([os.environ.get('AWS_CLI', 'aws'), *args, '--output', 'json'], capture_output=True, text=True, timeout=45, check=False)
    if result.returncode:
        raise ValueError('AWS read or route creation was denied or failed')
    return json.loads(result.stdout) if result.stdout.strip() else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('account', 'region', 'stack', 'vpc', 'table', 'eni', 'destination'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--apply', action='store_true', help='create the route only if absent')
    a = parser.parse_args()
    try:
        if not (re.fullmatch(r'\d{12}', a.account) and re.fullmatch(r'[a-z0-9-]+', a.region) and
                re.fullmatch(r'tangamandapio-live-\d{8}', a.stack) and
                re.fullmatch(r'vpc-[a-f0-9]+', a.vpc) and re.fullmatch(r'rtb-[a-f0-9]+', a.table) and
                re.fullmatch(r'eni-[a-f0-9]+', a.eni)):
            raise ValueError('Invalid account, region, stack or resource identifier')
        if aws('sts', 'get-caller-identity', '--region', a.region).get('Account') != a.account:
            raise ValueError('AWS account does not match')
        interface = aws('ec2', 'describe-network-interfaces', '--region', a.region, '--network-interface-ids', a.eni)['NetworkInterfaces'][0]
        instance_id = interface['Attachment']['InstanceId']
        if not re.fullmatch(r'i-[a-f0-9]+', instance_id):
            raise ValueError('Invalid router instance')
        instance = aws('ec2', 'describe-instances', '--region', a.region, '--instance-ids', instance_id)['Reservations'][0]['Instances'][0]
        validate_router(instance, interface, a.vpc, a.eni)
        table = aws('ec2', 'describe-route-tables', '--region', a.region, '--route-table-ids', a.table)['RouteTables'][0]
        action = assess_route(table, a.vpc, a.stack, a.eni, a.destination)
        if action == 'create' and a.apply:
            aws('ec2', 'create-route', '--region', a.region, '--route-table-id', a.table,
                '--destination-cidr-block', a.destination + '/32', '--network-interface-id', a.eni)
            # A route's existence is not proof of end-to-end connectivity.
            table = aws('ec2', 'describe-route-tables', '--region', a.region, '--route-table-ids', a.table)['RouteTables'][0]
            if assess_route(table, a.vpc, a.stack, a.eni, a.destination) != 'unchanged':
                raise ValueError('Route creation could not be verified')
            action = 'created'
        print(json.dumps({'route': action, 'connectivity_verified': False}))
        return 0
    except (ValueError, KeyError, IndexError, TypeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print('Route not changed: ' + (str(exc) if isinstance(exc, ValueError) else 'verification failed'), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
