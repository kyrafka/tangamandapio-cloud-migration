import importlib.util
import base64
import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch


APP_PATH = Path(__file__).resolve().parents[1] / "current" / "app.py"
_bootstrap_dir = tempfile.TemporaryDirectory(prefix="portal-release-import-")
_import_environment = {
    "DATABASE_URL": "",
    "DATABASE_PATH": str(Path(_bootstrap_dir.name) / "bootstrap.sqlite3"),
    "APP_SESSION_SECRET": "test-only-bootstrap-secret",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "DB_SECRET_ARN": "",
    "VOICE_RECORDINGS_BUCKET": "",
    "VOICE_RECORDINGS_ENABLED": "false",
}
with patch.dict(os.environ, _import_environment):
    if str(APP_PATH.parent) not in sys.path:
        sys.path.insert(0, str(APP_PATH.parent))
    spec = importlib.util.spec_from_file_location("portal_aws_release", APP_PATH)
    portal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(portal)


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.put_calls = []
        self.deleted = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, *, Bucket, Key):
        return {"Body": BytesIO(self.objects[(Bucket, Key)])}

    def delete_object(self, *, Bucket, Key):
        self.deleted.append((Bucket, Key))
        self.objects.pop((Bucket, Key), None)


class VoiceRecordingsS3TestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="portal-release-test-")
        self.database_path = str(Path(self.tempdir.name) / "portal.sqlite3")
        self.recordings_dir = str(Path(self.tempdir.name) / "local-recordings")
        self.s3 = FakeS3()
        self.app = portal.create_app(
            {
                "TESTING": True,
                "DATABASE_URL": "",
                "DATABASE_PATH": self.database_path,
                "SECRET_KEY": "test-session-secret-with-enough-entropy",
                "BOOTSTRAP_ADMIN_USERNAME": "admin@example.test",
                "BOOTSTRAP_ADMIN_PASSWORD": "Admin-Password-For-Tests-2026",
                "VOICE_RECORDINGS_DIR": self.recordings_dir,
                "VOICE_RECORDINGS_BUCKET": "tangamandapio-voice-test",
                "VOICE_RECORDINGS_PREFIX": "voice-recordings",
                "VOICE_RECORDINGS_ENABLED": True,
                "VOICE_RECORDING_S3_CLIENT": self.s3,
                "AUTO_DISPATCH_EVENTS": False,
            }
        )
        self.admin, self.admin_csrf = self.login(
            "admin@example.test", "Admin-Password-For-Tests-2026"
        )
        self.company_id = self.admin.get("/api/auth/session").get_json()["user"]["company_id"]
        self.sales_id = self.create_user("sales@example.test", "sales")
        self.operations_id = self.create_user("operations@example.test", "operations")

    def tearDown(self):
        self.tempdir.cleanup()

    def login(self, username, password):
        client = self.app.test_client()
        csrf = client.get("/api/auth/session").get_json()["csrf_token"]
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        csrf = client.get("/api/auth/session").get_json()["csrf_token"]
        return client, csrf

    def create_user(self, username, role):
        response = self.admin.post(
            "/api/admin/users",
            json={
                "username": username,
                "password": "Temporary-Password-2026",
                "role": role,
                "company_id": self.company_id,
            },
            headers={"X-CSRF-Token": self.admin_csrf},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["user"]["id"]

    def create_outbox_event(self):
        sales, sales_csrf = self.login("sales@example.test", "Temporary-Password-2026")
        response = sales.post(
            "/api/orders",
            json={"customer": "Cliente de prueba WMS", "reference": "WMS-TEST-01", "total": 12.5},
            headers={"X-CSRF-Token": sales_csrf},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["fulfillment"]["event_id"]

    def test_default_bucket_is_derived_from_the_deployment_secret_arn(self):
        self.assertEqual(
            portal.default_voice_recordings_bucket(
                "arn:aws:secretsmanager:us-east-1:000000000000:secret:tangamandapio/rds/master-AbC123"
            ),
            "tangamandapio-voice-000000000000-us-east-1",
        )
        self.assertEqual(portal.default_voice_recordings_bucket(""), "")

    def test_late_sign_in_can_answer_and_consented_audio_is_private_in_s3(self):
        sales, sales_csrf = self.login("sales@example.test", "Temporary-Password-2026")
        call_response = sales.post(
            "/api/voice/calls",
            json={"callee_id": self.operations_id},
            headers={"X-CSRF-Token": sales_csrf},
        )
        self.assertEqual(call_response.status_code, 201, call_response.get_json())
        call_id = call_response.get_json()["id"]

        offer = sales.post(
            f"/api/voice/calls/{call_id}/signals",
            json={"kind": "offer", "payload": {"sdp": "offer-from-before-peer-login"}},
            headers={"X-CSRF-Token": sales_csrf},
        )
        self.assertEqual(offer.status_code, 200, offer.get_json())

        # The callee signs in only after the call and offer have already been created.
        operations, operations_csrf = self.login(
            "operations@example.test", "Temporary-Password-2026"
        )
        incoming = operations.get("/api/voice/calls").get_json()
        self.assertTrue(any(row["id"] == call_id and row["status"] == "ringing" for row in incoming))
        received_offer = operations.get(f"/api/voice/calls/{call_id}/signals").get_json()
        self.assertEqual([signal["kind"] for signal in received_offer], ["offer"])

        answer = operations.post(
            f"/api/voice/calls/{call_id}/signals",
            json={"kind": "answer", "payload": {"sdp": "answer-after-login"}},
            headers={"X-CSRF-Token": operations_csrf},
        )
        self.assertEqual(answer.status_code, 200, answer.get_json())
        self.assertEqual(sales.get(f"/api/voice/calls/{call_id}/signals").get_json()[0]["kind"], "answer")

        recording_request = sales.post(
            f"/api/voice/calls/{call_id}/recording/request",
            headers={"X-CSRF-Token": sales_csrf},
        )
        self.assertEqual(recording_request.status_code, 201)
        blocked_start = sales.post(
            f"/api/voice/calls/{call_id}/recording/start",
            headers={"X-CSRF-Token": sales_csrf},
        )
        self.assertEqual(blocked_start.status_code, 409)
        consent = operations.post(
            f"/api/voice/calls/{call_id}/recording/consent",
            json={"consent": True},
            headers={"X-CSRF-Token": operations_csrf},
        )
        self.assertEqual(consent.status_code, 200)

        started = sales.post(
            f"/api/voice/calls/{call_id}/recording/start",
            headers={"X-CSRF-Token": sales_csrf},
        )
        self.assertEqual(started.status_code, 200)
        stopped = sales.post(
            f"/api/voice/calls/{call_id}/recording/stop",
            headers={"X-CSRF-Token": sales_csrf},
        )
        self.assertEqual(stopped.status_code, 200)

        audio = b"synthetic-audio-payload"
        uploaded = sales.post(
            f"/api/voice/calls/{call_id}/recording/upload",
            data={"recording": (BytesIO(audio), "call.webm", "audio/webm")},
            headers={"X-CSRF-Token": sales_csrf},
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.get_json())
        self.assertEqual(len(self.s3.put_calls), 1)
        put = self.s3.put_calls[0]
        self.assertEqual(put["Bucket"], "tangamandapio-voice-test")
        self.assertTrue(put["Key"].startswith("voice-recordings/rec-"))
        self.assertEqual(put["ServerSideEncryption"], "AES256")
        self.assertEqual(put["ContentType"], "audio/webm")
        self.assertNotIn("ACL", put)

        recordings = self.admin.get("/api/voice/recordings").get_json()
        self.assertTrue(recordings["enabled"])
        self.assertEqual(len(recordings["recordings"]), 1)
        file_response = self.admin.get(recordings["recordings"][0]["file_url"])
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(file_response.data, audio)
        self.assertEqual(file_response.headers["Cache-Control"], "private, no-store")
        video_upload = sales.post(
            f"/api/voice/calls/{call_id}/recording/upload",
            data={"recording": (BytesIO(b"video-payload"), "call.webm", "video/webm")},
            headers={"X-CSRF-Token": sales_csrf},
            content_type="multipart/form-data",
        )
        self.assertEqual(video_upload.status_code, 415)
        self.assertEqual(len(self.s3.put_calls), 1)

        with portal.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE voice_recordings SET expires_at = ? WHERE call_id = ?",
                ("2000-01-01T00:00:00+00:00", call_id),
            )
            connection.commit()
        portal.purge_expired_voice_recordings(
            self.database_path,
            self.recordings_dir,
            now_text="2001-01-01T00:00:00+00:00",
            s3_client=self.s3,
            s3_bucket="tangamandapio-voice-test",
            s3_prefix="voice-recordings",
        )
        self.assertEqual(len(self.s3.deleted), 1)
        self.assertEqual(self.s3.objects, {})
        self.assertEqual(self.admin.get("/api/voice/recordings").get_json()["recordings"], [])

    def test_admin_user_updates_revoke_existing_sessions_and_protect_self(self):
        sales, _ = self.login("sales@example.test", "Temporary-Password-2026")
        blocked = self.admin.patch(
            f"/api/admin/users/{self.sales_id}",
            json={"active": False},
            headers={"X-CSRF-Token": self.admin_csrf},
        )
        self.assertEqual(blocked.status_code, 200, blocked.get_json())
        self.assertEqual(sales.get("/api/auth/session").get_json()["authenticated"], False)

        self_block = self.admin.patch(
            f"/api/admin/users/{self.admin.get('/api/auth/session').get_json()['user']['id']}",
            json={"active": False},
            headers={"X-CSRF-Token": self.admin_csrf},
        )
        self.assertEqual(self_block.status_code, 409)
        self.assertEqual(self_block.get_json()["error"], "cannot_remove_own_admin_access")

    def test_admin_password_reset_requires_rotation_and_revokes_sessions(self):
        old_session, _ = self.login("sales@example.test", "Temporary-Password-2026")
        response = self.admin.post(
            f"/api/admin/users/{self.sales_id}/reset-password",
            headers={"X-CSRF-Token": self.admin_csrf},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        temporary_password = response.get_json()["temporary_password"]
        self.assertEqual(response.get_json()["user"]["must_change_password"], True)
        self.assertTrue(response.get_json()["reveal_once"])
        self.assertFalse(old_session.get("/api/auth/session").get_json()["authenticated"])

        forced_user, forced_csrf = self.login("sales@example.test", temporary_password)
        self.assertEqual(
            forced_user.get("/api/dashboard").status_code,
            428,
        )
        changed = forced_user.post(
            "/api/auth/password",
            json={
                "current_password": temporary_password,
                "new_password": "New-Long-Password-2026!",
            },
            headers={"X-CSRF-Token": forced_csrf},
        )
        self.assertEqual(changed.status_code, 200, changed.get_json())
        self.assertFalse(forced_user.get("/api/auth/session").get_json()["authenticated"])
        new_user, _ = self.login("sales@example.test", "New-Long-Password-2026!")
        self.assertFalse(new_user.get("/api/auth/session").get_json()["user"]["must_change_password"])

    def test_non_admin_cannot_manage_users(self):
        sales, sales_csrf = self.login("sales@example.test", "Temporary-Password-2026")
        response = sales.patch(
            f"/api/admin/users/{self.operations_id}",
            json={"role": "admin"},
            headers={"X-CSRF-Token": sales_csrf},
        )
        self.assertEqual(response.status_code, 403)

    def test_turn_credentials_are_short_lived_and_signed_per_user(self):
        sales, _ = self.login("sales@example.test", "Temporary-Password-2026")
        self.app.config.update(
            WEBRTC_TURN_URLS=("turn:turn.example.test:3478?transport=udp",),
            WEBRTC_TURN_SHARED_SECRET="test-turn-secret-never-used-in-production",
            WEBRTC_TURN_CREDENTIAL_TTL_SECONDS=120,
        )
        response = sales.get("/api/voice/ice-config")
        self.assertEqual(response.status_code, 200, response.get_json())
        result = response.get_json()
        self.assertTrue(result["turn_configured"])
        self.assertEqual(result["ice_servers"][0]["urls"], "stun:stun.l.google.com:19302")
        turn = result["ice_servers"][1]
        self.assertEqual(turn["urls"], "turn:turn.example.test:3478?transport=udp")
        expires, user_id = turn["username"].split(":", 1)
        self.assertEqual(int(user_id), self.sales_id)
        expected = base64.b64encode(
            hmac.new(
                b"test-turn-secret-never-used-in-production",
                turn["username"].encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("ascii")
        self.assertEqual(turn["credential"], expected)
        self.assertLessEqual(int(expires), int(time.time()) + 120)
        self.assertGreater(int(expires), int(time.time()))

    def test_outbox_status_reads_azure_result_and_labels_simulation(self):
        event_id = self.create_outbox_event()
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")
        self.app.config.update(
            AZURE_FULFILLMENT_URL="https://wms.example.test/api/fulfillment/events",
            AZURE_FUNCTION_KEY="function-test-key",
        )
        response_body = {
            "event_id": event_id,
            "status": "simulated_completed",
            "mode": "demo-only",
            "note": "No se modificó inventario real.",
        }
        with patch.object(
            portal, "urlopen", return_value=BytesIO(json.dumps(response_body).encode())
        ) as upstream:
            response = operations.get(f"/api/outbox/{event_id}/fulfillment-status")

        self.assertEqual(response.status_code, 200, response.get_json())
        result = response.get_json()
        self.assertEqual(result["provider"], "Azure")
        self.assertEqual(result["fulfillment_status"], "simulated_completed")
        self.assertTrue(result["simulated"])
        request = upstream.call_args.args[0]
        self.assertEqual(request.full_url, f"https://wms.example.test/api/fulfillment/events/{event_id}")
        headers = {name.lower(): value for name, value in request.header_items()}
        self.assertEqual(headers["x-functions-key"], "function-test-key")

    def test_outbox_status_is_role_restricted_and_requires_local_event(self):
        event_id = self.create_outbox_event()
        sales, _ = self.login("sales@example.test", "Temporary-Password-2026")
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")

        with patch.object(portal, "urlopen") as upstream:
            denied = sales.get(f"/api/outbox/{event_id}/fulfillment-status")
            missing = operations.get("/api/outbox/evt-not-found-01/fulfillment-status")
            invalid = operations.get("/api/outbox/evt-not.allowed/fulfillment-status")

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(invalid.status_code, 400)
        upstream.assert_not_called()

    def test_outbox_status_fails_closed_when_azure_access_is_not_configured(self):
        event_id = self.create_outbox_event()
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")
        self.app.config.update(
            AZURE_FULFILLMENT_URL="https://wms.example.test",
            AZURE_FUNCTION_KEY="",
        )

        with patch.object(portal, "urlopen") as upstream:
            response = operations.get(f"/api/outbox/{event_id}/fulfillment-status")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "not_configured")
        upstream.assert_not_called()

    def test_outbox_status_hides_azure_function_key_rejection_details(self):
        event_id = self.create_outbox_event()
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")
        self.app.config.update(
            AZURE_FULFILLMENT_URL="https://wms.example.test",
            AZURE_FUNCTION_KEY="function-test-key",
        )
        upstream_error = HTTPError(
            "https://wms.example.test/api/fulfillment/events/evt-test-event",
            401,
            "Unauthorized",
            {},
            BytesIO(b"function key rejected: do-not-leak-this-detail"),
        )

        with patch.object(portal, "urlopen", side_effect=upstream_error):
            response = operations.get(f"/api/outbox/{event_id}/fulfillment-status")

        self.assertEqual(response.status_code, 502)
        result = response.get_json()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["error"], "upstream_http_error")
        self.assertNotIn("function-test-key", response.get_data(as_text=True))
        self.assertNotIn("do-not-leak-this-detail", response.get_data(as_text=True))
        upstream_error.close()

    def test_outbox_dispatch_accepts_azure_duplicate_queue_ack(self):
        event_id = self.create_outbox_event()
        self.app.config.update(
            AZURE_FULFILLMENT_URL="https://wms.example.test",
            AZURE_FUNCTION_KEY="function-test-key",
        )
        response_body = {"event_id": event_id, "status": "queued_duplicate"}

        with patch.object(
            portal, "urlopen", return_value=BytesIO(json.dumps(response_body).encode())
        ):
            result = portal.dispatch_outbox_event(self.app, self.database_path, event_id)

        self.assertEqual(result["status"], "delivered")
        self.assertEqual(result["upstream"], "queued_duplicate")
        with portal.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT status, attempts FROM outbox_events WHERE event_id = ?", (event_id,)
            ).fetchone()
        self.assertEqual(row["status"], "delivered")
        self.assertEqual(row["attempts"], 1)


if __name__ == "__main__":
    unittest.main()
