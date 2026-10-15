import os
import re
import tempfile
import unittest
from pathlib import Path

_test_root = tempfile.TemporaryDirectory(prefix="tangamandapio-cache-tests-")
os.environ.setdefault("DATABASE_PATH", str(Path(_test_root.name) / "module-import.db"))
os.environ.setdefault("APP_SESSION_SECRET", "cache-policy-test-secret-not-for-production")
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "admin@cache.test")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "Cache-Policy-Test-Only-2026!")

import app as portal


class StaticCachePolicyTests(unittest.TestCase):
    def setUp(self):
        self._database = tempfile.TemporaryDirectory(prefix="tangamandapio-cache-db-")
        self.application = portal.create_app(
            {
                "TESTING": True,
                "DATABASE_URL": "",
                "DATABASE_PATH": str(Path(self._database.name) / "portal.sqlite"),
                "APP_SESSION_SECRET": "cache-policy-test-secret-not-for-production",
                "BOOTSTRAP_ADMIN_USERNAME": "admin@cache.test",
                "BOOTSTRAP_ADMIN_PASSWORD": "Cache-Policy-Test-Only-2026!",
                "INTERNAL_ERP_ENABLED": False,
            }
        )
        self.client = self.application.test_client()

    def tearDown(self):
        self._database.cleanup()

    def test_document_revalidates_and_api_is_not_stored(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(
            page.headers["Cache-Control"],
            "no-cache, max-age=0, must-revalidate",
        )
        self.assertIn(b"data-landing-art", page.data)
        self.assertIn(b"walpurgis-rising-pixel-diffused-v1.png", page.data)
        self.assertIn(b"accessibility-drawer-7f1356105ee4.js", page.data)

        health = self.client.get("/health")
        self.assertEqual(health.headers["Cache-Control"], "no-store")

    def test_hashed_assets_and_semantically_versioned_image_are_immutable(self):
        page = self.client.get("/")
        assets = re.findall(rb'(?:src|href)="(/assets/[^\"]+)"', page.data)
        page.close()
        fingerprinted = [
            path.decode("ascii")
            for path in assets
            if re.fullmatch(
                r"/assets/(?:index-[A-Za-z0-9_-]{8,}\.(?:js|css)|"
                r"landing-art-[0-9a-f]{12}\.(?:css|js)|"
                r"accessibility-drawer-[0-9a-f]{12}\.js)",
                path.decode("ascii"),
            )
        ]
        self.assertGreaterEqual(len(fingerprinted), 4)

        for asset_path in fingerprinted:
            with self.subTest(asset=asset_path):
                response = self.client.get(asset_path)
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        response.headers["Cache-Control"],
                        "public, max-age=31536000, immutable",
                    )
                finally:
                    response.close()

        image = self.client.head(
            "/images/walpurgis-rising-pixel-diffused-v1.png"
        )
        try:
            self.assertEqual(image.status_code, 200)
            self.assertTrue(image.headers["Content-Type"].startswith("image/png"))
            self.assertEqual(
                image.headers["Cache-Control"],
                "public, max-age=31536000, immutable",
            )
        finally:
            image.close()

    def test_authenticated_portal_does_not_preload_landing_art(self):
        csrf = self.client.get("/api/auth/session").get_json()["csrf_token"]
        login = self.client.post(
            "/api/auth/login",
            json={"username": "admin@cache.test", "password": "Cache-Policy-Test-Only-2026!"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(login.status_code, 200)
        page = self.client.get("/")
        try:
            self.assertNotIn(b"data-landing-art", page.data)
        finally:
            page.close()

    def test_admin_and_platform_pages_reference_existing_styles(self):
        csrf = self.client.get("/api/auth/session").get_json()["csrf_token"]
        login = self.client.post(
            "/api/auth/login",
            json={"username": "admin@cache.test", "password": "Cache-Policy-Test-Only-2026!"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(login.status_code, 200)

        for page_path in ("/administracion", "/platform"):
            with self.subTest(page=page_path):
                page = self.client.get(page_path)
                try:
                    self.assertEqual(page.status_code, 200)
                    self.assertNotIn(b"index-KzEIokgC.css", page.data)
                    assets = re.findall(
                        rb'href="(/assets/[^\"]+\.css)"', page.data
                    )
                    self.assertTrue(assets)
                finally:
                    page.close()

                for asset_path in assets:
                    asset = self.client.get(asset_path.decode("ascii"))
                    try:
                        self.assertEqual(asset.status_code, 200)
                        expected_cache_control = (
                            "public, max-age=31536000, immutable"
                            if re.fullmatch(
                                rb"/assets/index-[A-Za-z0-9_-]{8,}\.css",
                                asset_path,
                            )
                            else "no-store"
                        )
                        self.assertEqual(
                            asset.headers["Cache-Control"], expected_cache_control
                        )
                    finally:
                        asset.close()

    def test_unversioned_static_shortcut_is_not_cached(self):
        response = self.client.get("/assets/platform-shortcut.js")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        finally:
            response.close()


if __name__ == "__main__":
    unittest.main()
