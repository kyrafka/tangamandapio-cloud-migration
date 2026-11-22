import json
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

import test_admin_recovery


class CloudToolsTests(unittest.TestCase):
    setUp = test_admin_recovery.AdministratorRecoveryTests.setUp
    tearDown = test_admin_recovery.AdministratorRecoveryTests.tearDown

    def test_admin_creates_and_downloads_a_private_outbox_checkpoint(self):
        self.application.config["ADMIN_BACKUP_BUCKET"] = "private-test-bucket"
        client = self.application.test_client()
        self.assertEqual(client.get("/api/admin/backups").status_code, 401)
        login = client.post("/api/auth/login", json={
            "username": "admin@recovery.test", "password": "Initial-Password-2026!",
        })
        self.assertEqual(login.status_code, 200)
        csrf = client.get("/api/auth/session").json["csrf_token"]
        self.assertEqual(client.post("/api/admin/backups").status_code, 403)
        s3 = MagicMock()
        with patch("admin_cloud_tools.aws_client", return_value=s3):
            result = client.post("/api/admin/backups", headers={"X-CSRF-Token": csrf})
            self.assertEqual(result.status_code, 201)
            saved = s3.put_object.call_args.kwargs
            self.assertEqual(saved["ServerSideEncryption"], "AES256")
            self.assertEqual(json.loads(saved["Body"])["outbox_events"], [])
            s3.get_object.return_value = {"Body": BytesIO(saved["Body"])}
            download = client.get(result.json["download"])
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download.get_data(), saved["Body"])
            self.assertIn("no-store", download.headers["Cache-Control"])

    def test_admin_can_monitor_policy_without_setting_capacity(self):
        self.application.config["ADMIN_SCALING_GROUP"] = "example-asg"
        client = self.application.test_client()
        self.assertEqual(client.get("/api/admin/scaling").status_code, 401)
        login = client.post("/api/auth/login", json={
            "username": "admin@recovery.test", "password": "Initial-Password-2026!",
        })
        self.assertEqual(login.status_code, 200)
        csrf = client.get("/api/auth/session").json["csrf_token"]
        autoscaling = MagicMock()
        autoscaling.describe_auto_scaling_groups.return_value = {"AutoScalingGroups": [{
            "MinSize": 2, "MaxSize": 5, "DesiredCapacity": 3, "Instances": [],
        }]}
        autoscaling.describe_scheduled_actions.return_value = {"ScheduledUpdateGroupActions": []}
        autoscaling.describe_policies.return_value = {"ScalingPolicies": [{"TargetTrackingConfiguration": {
            "PredefinedMetricSpecification": {"PredefinedMetricType": "ALBRequestCountPerTarget"},
            "TargetValue": 2500,
        }}]}
        with patch("admin_cloud_tools.aws_client", return_value=autoscaling):
            self.assertEqual(client.post("/api/admin/scaling", json={"capacity": 4},
                                        headers={"X-CSRF-Token": csrf}).status_code, 405)
            group = client.get("/api/admin/scaling")
        self.assertEqual(group.status_code, 200)
        self.assertEqual(group.json["desired"], 3)
        self.assertEqual(group.json["requests_per_target"], 2500)
        self.assertIn("no-store", group.headers["Cache-Control"])
