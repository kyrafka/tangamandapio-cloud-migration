#!/usr/bin/env python3
"""Prepare, but never publish, scoped Tangamandapio Tailscale policy changes.

Input must be a normalized JSON copy of the actual policy. Review the output
and permissions before publishing; this script does not enroll devices or
change a tailnet. Existing user-tagged devices keep their identities.
"""
import argparse
import copy
import json
import sys

AWS_TAG = 'tag:tangama-aws-router'
AZURE_TAG = 'tag:tangama-azure-router'
GRANT = {'src': [AWS_TAG], 'dst': ['10.20.1.4/32'], 'ip': ['tcp:443']}


def prepare(policy):
    if not isinstance(policy, dict):
        raise ValueError('policy must be a JSON object')
    result = copy.deepcopy(policy)
    owners = result.setdefault('tagOwners', {})
    grants = result.setdefault('grants', [])
    auto = result.setdefault('autoApprovers', {})
    if not isinstance(owners, dict) or not isinstance(grants, list) or not isinstance(auto, dict):
        raise ValueError('unsupported policy format')
    routes = auto.setdefault('routes', {})
    if not isinstance(routes, dict):
        raise ValueError('unsupported routes format')
    for tag in (AWS_TAG, AZURE_TAG):
        if tag in owners and owners[tag] != ['autogroup:admin']:
            raise ValueError('project tag ownership already differs; manual review required')
        owners[tag] = ['autogroup:admin']
    approvers = routes.setdefault('10.20.1.0/24', [])
    if not isinstance(approvers, list):
        raise ValueError('unsupported route approvers')
    if AZURE_TAG not in approvers:
        approvers.append(AZURE_TAG)
    if GRANT not in grants:
        grants.append(copy.deepcopy(GRANT))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('policy', help='normalized current policy JSON')
    args = parser.parse_args()
    try:
        with open(args.policy, encoding='utf-8') as source:
            result = prepare(json.load(source))
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f'Policy not changed: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
