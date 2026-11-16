import unittest
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


class AutoScalingNotificationTests(unittest.TestCase):
    def test_asg_publishes_launch_and_termination_events_to_alarm_topic(self):
        template = (ROOT / "iac/cloudformation/aws-lab.yaml").read_text(encoding="utf-8")
        match = re.search(r"(?ms)^  AutoScalingGroup:\n(.*?)(?=^  \S)", template)
        self.assertIsNotNone(match, "Auto Scaling group resource is missing")
        block = match.group(1)

        self.assertIn("NotificationConfigurations:", block)
        self.assertIn("TopicARN: !Ref AlarmNotificationTopic", block)
        for event in (
            "autoscaling:EC2_INSTANCE_LAUNCH",
            "autoscaling:EC2_INSTANCE_LAUNCH_ERROR",
            "autoscaling:EC2_INSTANCE_TERMINATE",
            "autoscaling:EC2_INSTANCE_TERMINATE_ERROR",
        ):
            self.assertIn(event, block)

    def test_custom_alarm_descriptions_explain_signal_threshold_and_response_in_spanish(self):
        template = (ROOT / "iac/cloudformation/aws-lab.yaml").read_text(encoding="utf-8")
        expected = {
            "HighCPUAlarm": ("70", "300", "cpu"),
            "UnhealthyTargetsAlarm": ("0", "60", "destino"),
            "InServiceCapacityAlarm": ("2", "60", "instancias"),
            "Target5xxAlarm": ("5", "60", "5xx"),
            "DatabaseCPUAlarm": ("75", "60", "postgres"),
        }
        for logical_id, (threshold, period, signal) in expected.items():
            with self.subTest(alarm=logical_id):
                match = re.search(rf"(?ms)^  {logical_id}:\n(.*?)(?=^  \S)", template)
                self.assertIsNotNone(match, f"{logical_id} alarm is missing")
                block = match.group(1).lower()
                self.assertRegex(block, r"alarmdescription: .+\n")
                description = re.search(r"(?m)^      alarmdescription: (.+)$", block).group(1)
                self.assertIn(signal, description)
                self.assertIn(threshold, block)
                self.assertIn(f"period: {period}", block)
                self.assertIn("alarmactions: [!ref alarmnotificationtopic]", block)
                self.assertTrue(any(word in description for word in ("notifica", "avisa", "sns")))


if __name__ == "__main__":
    unittest.main()
