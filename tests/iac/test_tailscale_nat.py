import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile

SOURCE = Path(__file__).resolve().parents[2] / 'iac/scripts/tailscale_nat.py'


def load():
    spec = importlib.util.spec_from_file_location('tailscale_nat', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScopedNatTests(unittest.TestCase):
    def test_service_limits_nat_to_application_wms_and_443(self):
        unit = load().render_service('10.10.10.0/23', '10.20.1.4')
        self.assertIn('-s 10.10.10.0/23 -d 10.20.1.4/32 -p tcp --dport 443 -o tailscale0', unit)
        self.assertIn('iptables -t nat -C POSTROUTING', unit)
        self.assertIn('iptables -t nat -A POSTROUTING', unit)
        self.assertNotIn('0.0.0.0/0', unit)

    def test_refuses_routes_outside_project_and_injected_values(self):
        mod = load()
        for source, target in [('0.0.0.0/0', '10.20.1.4'), ('10.10.10.0/23', '8.8.8.8'), ('10.10.10.0/23;bad', '10.20.1.4'), ('10.10.10.1/23', '10.20.1.4')]:
            with self.subTest(source=source, target=target), self.assertRaises(ValueError):
                mod.render_service(source, target)

    def test_refuses_a_whole_vpc_as_nat_source(self):
        with self.assertRaises(ValueError):
            load().render_service('10.10.0.0/16', '10.20.1.4')

    def test_conflicting_unit_is_not_overwritten_and_no_command_runs(self):
        mod = load()
        with tempfile.TemporaryDirectory() as directory:
            unit = Path(directory) / 'unit'
            setting = Path(directory) / 'setting'
            unit.write_text('unrelated policy', encoding='utf8')
            with patch.object(mod.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    mod.install('10.10.10.0/23', '10.20.1.4', unit, setting)
                run.assert_not_called()
            self.assertEqual(unit.read_text(encoding='utf8'), 'unrelated policy')
            self.assertFalse(setting.exists())

    def test_install_is_idempotent_and_keeps_other_files(self):
        mod = load()
        with tempfile.TemporaryDirectory() as directory:
            unit = Path(directory) / 'unit'
            setting = Path(directory) / 'setting'
            other = Path(directory) / 'unrelated'
            other.write_text('keep', encoding='utf8')
            with patch.object(mod.subprocess, 'run') as run:
                mod.install('10.10.10.0/23', '10.20.1.4', unit, setting)
                first = unit.read_text(encoding='utf8')
                mod.install('10.10.10.0/23', '10.20.1.4', unit, setting)
                self.assertEqual(unit.read_text(encoding='utf8'), first)
                self.assertEqual(setting.read_text(encoding='utf8'), 'net.ipv4.ip_forward=1\n')
                self.assertTrue(run.called)
            self.assertEqual(other.read_text(encoding='utf8'), 'keep')
