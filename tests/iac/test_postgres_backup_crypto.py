import importlib.util
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

SCRIPT = Path(__file__).resolve().parents[2] / 'iac' / 'scripts' / 'postgres_backup_crypto.py'


class BackupCryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.exists():
            return
        spec = importlib.util.spec_from_file_location('backup_crypto', SCRIPT)
        cls.crypto = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.crypto)

    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'backup encryption implementation is missing')
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_pem = self.private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def unwrap(self, data):
        return self.private_key.decrypt(data, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))

    def test_roundtrip_does_not_store_plaintext_and_uses_versioned_key(self):
        data = b'synthetic confidential database archive'
        packed = self.crypto.seal(data, self.public_pem, 'https://example.vault.azure.net/keys/dr/version1')
        self.assertNotIn(data, packed)
        self.assertEqual(self.crypto.open_envelope(packed, self.unwrap), data)

    def test_tampered_ciphertext_and_header_are_rejected(self):
        packed = self.crypto.seal(b'synthetic content', self.public_pem, 'https://example.vault.azure.net/keys/dr/version1')
        envelope = json.loads(packed)
        envelope['key_id'] += 'changed'
        with self.assertRaises(Exception):
            self.crypto.open_envelope(json.dumps(envelope).encode(), self.unwrap)
        envelope = json.loads(packed)
        envelope['ciphertext'] = ('A' if envelope['ciphertext'][0] != 'A' else 'B') + envelope['ciphertext'][1:]
        with self.assertRaises(Exception):
            self.crypto.open_envelope(json.dumps(envelope).encode(), self.unwrap)

    def test_refuses_unversioned_key_identifier(self):
        with self.assertRaises(ValueError):
            self.crypto.seal(b'data', self.public_pem, 'https://example.vault.azure.net/keys/dr')

    def test_rejects_invalid_envelopes_before_unwrap(self):
        called = []
        with self.assertRaises(ValueError):
            self.crypto.open_envelope(b'{"format":"wrong"}', lambda data: called.append(data))
        self.assertFalse(called)


if __name__ == '__main__':
    unittest.main()
