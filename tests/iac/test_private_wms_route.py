import importlib.util
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[2] / 'iac/scripts/ensure_private_wms_route.py'


def load():
    spec = importlib.util.spec_from_file_location('private_route', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def table(routes):
    return {'VpcId': 'vpc-1234', 'Tags': [{'Key': 'aws:cloudformation:stack-name', 'Value': 'tangamandapio-live-20261104'}, {'Key': 'aws:cloudformation:logical-id', 'Value': 'AppRouteTable'}], 'Routes': routes}


class RouteTests(unittest.TestCase):
    def test_apply_does_not_mutate_an_existing_correct_route(self):
        mod = load()
        route = {'DestinationCidrBlock': '10.20.1.4/32', 'NetworkInterfaceId': 'eni-1234', 'State': 'active'}
        interface = {'NetworkInterfaceId': 'eni-1234', 'VpcId': 'vpc-1234', 'SourceDestCheck': False, 'Attachment': {'InstanceId':'i-1234'}}
        instance = {'InstanceId': 'i-1234', 'State': {'Name': 'running'}, 'VpcId': 'vpc-1234', 'Tags': [{'Key':'Project','Value':'Tangamandapio'}, {'Key':'aws:cloudformation:stack-name','Value':'tangamandapio-tailscale-pilot'}]}
        def aws(*args):
            if args[:2] == ('sts', 'get-caller-identity'): return {'Account':'654654388734'}
            if args[:2] == ('ec2', 'describe-network-interfaces'): return {'NetworkInterfaces':[interface]}
            if args[:2] == ('ec2', 'describe-instances'): return {'Reservations':[{'Instances':[instance]}]}
            if args[:2] == ('ec2', 'describe-route-tables'): return {'RouteTables':[table([route])]}
            raise AssertionError('No route mutation is allowed')
        argv = ['tool', '--account','654654388734','--region','us-east-1','--stack','tangamandapio-live-20261104','--vpc','vpc-1234','--table','rtb-1234','--eni','eni-1234','--destination','10.20.1.4','--apply']
        with patch.object(mod, 'aws', side_effect=aws), patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mod.main(), 0)

    def test_absent_exact_route_is_created_only_in_project_table(self):
        module = load()
        self.assertEqual(module.assess_route(table([]), 'vpc-1234', 'tangamandapio-live-20261104', 'eni-1234', '10.20.1.4'), 'create')

    def test_existing_exact_route_is_idempotent(self):
        route = {'DestinationCidrBlock': '10.20.1.4/32', 'NetworkInterfaceId': 'eni-1234', 'State': 'active'}
        self.assertEqual(load().assess_route(table([route]), 'vpc-1234', 'tangamandapio-live-20261104', 'eni-1234', '10.20.1.4'), 'unchanged')

    def test_route_to_other_router_or_other_table_is_never_overwritten(self):
        mod = load()
        route = {'DestinationCidrBlock': '10.20.1.4/32', 'NetworkInterfaceId': 'eni-9999', 'State': 'active'}
        with self.assertRaises(ValueError):
            mod.assess_route(table([route]), 'vpc-1234', 'tangamandapio-live-20261104', 'eni-1234', '10.20.1.4')
        with self.assertRaises(ValueError):
            mod.assess_route(table([]), 'vpc-9999', 'tangamandapio-live-20261104', 'eni-1234', '10.20.1.4')

    def test_rejects_non_project_endpoint_and_stopped_or_foreign_router(self):
        mod = load()
        with self.assertRaises(ValueError):
            mod.assess_route(table([]), 'vpc-1234', 'tangamandapio-live-20261104', 'eni-1234', '8.8.8.8')
        router = {'InstanceId': 'i-1234', 'State': {'Name': 'stopped'}, 'VpcId': 'vpc-1234', 'Tags': [{'Key':'Project','Value':'Tangamandapio'}, {'Key':'aws:cloudformation:stack-name','Value':'tangamandapio-tailscale-pilot'}]}
        eni = {'NetworkInterfaceId':'eni-1234', 'VpcId':'vpc-1234', 'SourceDestCheck': False, 'Attachment': {'InstanceId':'i-1234'}}
        with self.assertRaises(ValueError):
            mod.validate_router(router, eni, 'vpc-1234', 'eni-1234')
