"""Authenticated envelope encryption for PostgreSQL backups.

The writer needs only a versioned Azure Key Vault public key.  Recovery must
provide an unwrap function backed by the matching protected private key.
"""
import base64
import json
import os
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT = 'tangamandapio-postgres-aesgcm-rsa-oaep256-v1'
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024


def _key_id(value):
    parsed = urlparse(value)
    parts = parsed.path.strip('/').split('/')
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.vault.azure.net') or parsed.query or parsed.fragment or len(parts) != 3 or parts[0] != 'keys' or not all(parts):
        raise ValueError('A versioned Azure Key Vault key identifier is required')
    return value


def _aad(key_id):
    return (FORMAT + '\n' + _key_id(key_id)).encode('utf-8')


def _b64(value):
    return base64.b64encode(value).decode('ascii')


def seal(data, public_key_pem, key_id):
    if not isinstance(data, bytes) or not data or len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError('Archive must be nonempty and at most 100 MiB')
    associated = _aad(key_id)
    key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048:
        raise ValueError('RSA public key must be at least 2048 bits')
    data_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    wrapped = key.encrypt(data_key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    encrypted = AESGCM(data_key).encrypt(nonce, data, associated)
    return json.dumps({'format': FORMAT, 'key_id': key_id, 'wrapped_key': _b64(wrapped), 'nonce': _b64(nonce), 'ciphertext': _b64(encrypted)}, separators=(',', ':')).encode('utf-8')


def open_envelope(payload, unwrap):
    if not isinstance(payload, bytes) or len(payload) > ((MAX_ARCHIVE_BYTES + 8192) * 4 // 3 + 8192):
        raise ValueError('Invalid envelope size')
    try:
        envelope = json.loads(payload)
        if set(envelope) != {'format', 'key_id', 'wrapped_key', 'nonce', 'ciphertext'} or envelope['format'] != FORMAT:
            raise ValueError('Invalid envelope fields')
        associated = _aad(envelope['key_id'])
        wrapped = base64.b64decode(envelope['wrapped_key'], validate=True)
        nonce = base64.b64decode(envelope['nonce'], validate=True)
        ciphertext = base64.b64decode(envelope['ciphertext'], validate=True)
        if len(wrapped) < 256 or len(wrapped) > 1024 or len(nonce) != 12 or len(ciphertext) < 17:
            raise ValueError('Invalid envelope data')
    except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
        raise ValueError('Malformed backup envelope') from exc
    data_key = unwrap(wrapped)
    if not isinstance(data_key, bytes) or len(data_key) != 32:
        raise ValueError('Invalid unwrapped key')
    return AESGCM(data_key).decrypt(nonce, ciphertext, associated)
