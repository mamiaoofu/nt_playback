"""
AES-256-GCM symmetric encryption utilities for storing sensitive values
(e.g. SMB passwords) in the database.

The 256-bit key is read from Django settings (SMB_ENCRYPTION_KEY), which
should be set via environment variable — never hard-coded.

Generate a key:
    python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"

Cipher format stored in DB (all base64url, colon-separated):
    <nonce_b64>:<ciphertext_b64>:<tag_b64>
"""

import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_UNSET = object()


def _get_key() -> bytes:
    """
    Return the 32-byte AES-256 key from Django settings.
    Raises RuntimeError if the key is missing or invalid.
    """
    from django.conf import settings as dj_settings
    raw = getattr(dj_settings, 'SMB_ENCRYPTION_KEY', '')
    if not raw:
        raise RuntimeError(
            'SMB_ENCRYPTION_KEY is not set. '
            'Add it to your .env / docker-compose environment.\n'
            'Generate: python -c "import secrets,base64;'
            'print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"'
        )
    try:
        key = base64.urlsafe_b64decode(raw + '==')  # tolerant of missing padding
    except Exception as exc:
        raise RuntimeError(f'SMB_ENCRYPTION_KEY is not valid base64: {exc}') from exc
    if len(key) != 32:
        raise RuntimeError(
            f'SMB_ENCRYPTION_KEY must decode to exactly 32 bytes (got {len(key)}).'
        )
    return key


def encrypt_smb_password(plaintext: str) -> str:
    """
    Encrypt *plaintext* with AES-256-GCM.
    Returns a string safe to store in the database:
        <nonce_b64>:<ciphertext_b64>:<tag_b64>
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)          # 96-bit nonce (GCM standard)
    ct_and_tag = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    # AESGCM.encrypt returns ciphertext || 16-byte tag concatenated
    ct   = ct_and_tag[:-16]
    tag  = ct_and_tag[-16:]
    b64  = base64.urlsafe_b64encode
    return f"{b64(nonce).decode()}:{b64(ct).decode()}:{b64(tag).decode()}"


def decrypt_smb_password(encrypted: str) -> str:
    """
    Decrypt a value produced by *encrypt_smb_password*.
    Returns the original plaintext string.
    Raises ValueError if the format is wrong or authentication fails.
    """
    if not encrypted:
        raise ValueError('Encrypted value is empty.')
    parts = encrypted.split(':')
    if len(parts) != 3:
        raise ValueError(
            'Unexpected encrypted format. Expected <nonce>:<ct>:<tag>.'
        )
    try:
        b64d = base64.urlsafe_b64decode
        nonce = b64d(parts[0] + '==')
        ct    = b64d(parts[1] + '==')
        tag   = b64d(parts[2] + '==')
    except Exception as exc:
        raise ValueError(f'Base64 decoding failed: {exc}') from exc

    key = _get_key()
    aesgcm = AESGCM(key)
    try:
        plaintext_bytes = aesgcm.decrypt(nonce, ct + tag, None)
    except Exception as exc:
        raise ValueError(f'Decryption failed (wrong key or tampered data): {exc}') from exc
    return plaintext_bytes.decode('utf-8')


def is_encrypted(value: str) -> bool:
    """Return True if *value* looks like an AES-256-GCM encrypted blob."""
    if not value:
        return False
    parts = value.split(':')
    return len(parts) == 3 and all(parts)
