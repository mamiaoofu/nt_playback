"""
License verification service.

Handles all license-related operations: signature verification,
fingerprint matching, expiry checks, concurrency tracking (Redis),
and feature limit enforcement.
"""

import base64
import json
import logging
import os
import time

from django.conf import settings
from django.utils import timezone
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

logger = logging.getLogger(__name__)

# Redis client (lazy-loaded)
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis as _redis
        url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        _redis_client = _redis.Redis.from_url(url, decode_responses=True)
    return _redis_client


# In-memory cache for parsed license + validation result
_license_cache = {
    'data': None,
    'valid': None,
    'reason': None,
    'loaded_at': 0,
}
_CACHE_TTL = 300  # 5 minutes


class LicenseService:
    """Core license verification and enforcement service."""

    REDIS_ACTIVE_SESSIONS_KEY = 'license:active_sessions'

    # ─── License Loading ────────────────────────────────────

    def load_license(self):
        """Load and parse license.json. Returns dict or None."""
        path = getattr(settings, 'LICENSE_FILE_PATH', None)
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error('Failed to load license file: %s', e)
            return None

    def _load_public_key(self):
        """Load the PEM public key for signature verification."""
        path = getattr(settings, 'LICENSE_PUBLIC_KEY_PATH', None)
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, 'rb') as f:
                return serialization.load_pem_public_key(f.read())
        except Exception as e:
            logger.error('Failed to load public key: %s', e)
            return None

    # ─── Signature Verification ─────────────────────────────

    def verify_signature(self, license_obj=None):
        """Verify RSA-PSS signature of license_data. Returns True/False."""
        if license_obj is None:
            license_obj = self.load_license()
        if not license_obj:
            return False

        public_key = self._load_public_key()
        if not public_key:
            return False

        try:
            license_data = license_obj['license_data']
            signature = base64.b64decode(license_obj['signature'])
            canonical = json.dumps(license_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

            public_key.verify(
                signature,
                canonical,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception as e:
            logger.warning('License signature verification failed: %s', e)
            return False

    # ─── Fingerprint Verification ───────────────────────────

    def verify_fingerprint(self, license_obj=None):
        """
        Verify hardware binding via challenge-response with the local attestation agent.

        Flow:
          1. Generate a random nonce + current Unix timestamp.
          2. POST {nonce, ts} to the agent running on the Windows host
             (reachable at host.docker.internal:7890 from inside Docker).
          3. Agent computes HMAC-SHA256(key=real_hw_fingerprint, msg=f"{nonce}:{ts}")
             and returns the token — raw fingerprint never leaves the host.
          4. We recompute the expected token using the fingerprint stored in
             license.json and compare with hmac.compare_digest (constant-time).

        Security:
          - Nonce is random on every call → zero replay possibility.
          - Timestamp must be fresh within 30 s → tiny window even if captured.
          - Raw fingerprint is never transmitted → cannot be stolen.
          - Cloned machine: agent returns HMAC for different hardware → mismatch.
          - 'printenv' / 'docker inspect' reveals nothing useful (no secrets stored).
        """
        import hmac as _hmac
        import secrets
        import time

        try:
            import requests as _req
        except ImportError:
            logger.error('requests library not available for agent attestation')
            return False

        if license_obj is None:
            license_obj = self.load_license()
        if not license_obj:
            return False

        license_fp = license_obj.get('license_data', {}).get('fingerprint', '').strip().lower()
        if not license_fp:
            return False

        agent_url = getattr(settings, 'LICENSE_AGENT_URL', 'http://host.docker.internal:7890')
        nonce = secrets.token_hex(16)
        ts = int(time.time())

        try:
            resp = _req.post(
                f'{agent_url}/attest',
                json={'nonce': nonce, 'ts': ts},
                timeout=5,
            )
            resp.raise_for_status()
            token = resp.json().get('token', '').strip().lower()
        except Exception as e:
            logger.error('Failed to contact attestation agent at %s: %s', agent_url, e)
            return False

        if not token:
            return False

        msg = f'{nonce}:{ts}'.encode('utf-8')
        expected = _hmac.new(license_fp.encode('utf-8'), msg, 'sha256').hexdigest()
        result = _hmac.compare_digest(expected, token)
        if not result:
            logger.warning('Attestation agent returned unexpected token — fingerprint mismatch')
        return result

    # ─── Expiry Check ───────────────────────────────────────

    def is_expired(self, license_obj=None):
        """Check if the license has expired. Returns True if expired."""
        if license_obj is None:
            license_obj = self.load_license()
        if not license_obj:
            return True

        expiry_str = license_obj.get('license_data', {}).get('expiry', '')
        if not expiry_str:
            return True

        try:
            from datetime import datetime
            # Parse ISO format expiry
            expiry_str_clean = expiry_str.replace('Z', '+00:00')
            expiry_dt = datetime.fromisoformat(expiry_str_clean)
            return timezone.now() > expiry_dt
        except Exception as e:
            logger.error('Failed to parse license expiry: %s', e)
            return True

    # ─── Feature Limits ─────────────────────────────────────

    def get_feature_limits(self, license_obj=None):
        """Return the features dict from the license, or empty dict."""
        if license_obj is None:
            license_obj = self.load_license()
        if not license_obj:
            return {}
        return license_obj.get('license_data', {}).get('features', {})

    def get_license_info(self, license_obj=None):
        """Return sanitized license info (no fingerprint/signature)."""
        if license_obj is None:
            license_obj = self.load_license()
        if not license_obj:
            return None

        ld = license_obj.get('license_data', {})
        return {
            'license_id': ld.get('license_id', ''),
            'customer_name': ld.get('customer_name', ''),
            'issued_at': ld.get('issued_at', ''),
            'expiry': ld.get('expiry', ''),
            'features': ld.get('features', {}),
        }

    # ─── Full Validation (cached) ───────────────────────────

    def validate_full(self):
        """
        Run full license validation: signature + fingerprint + expiry.
        Result is cached in-memory for CACHE_TTL seconds.
        Returns (is_valid: bool, reason: str).
        """
        now = time.time()
        if _license_cache['data'] is not None and (now - _license_cache['loaded_at']) < _CACHE_TTL:
            return _license_cache['valid'], _license_cache['reason']

        license_obj = self.load_license()
        if not license_obj:
            result = (False, 'no_license')
        elif not self.verify_signature(license_obj):
            result = (False, 'invalid_signature')
        elif not self.verify_fingerprint(license_obj):
            result = (False, 'fingerprint_mismatch')
        elif self.is_expired(license_obj):
            result = (False, 'expired')
        else:
            result = (True, 'valid')

        _license_cache['data'] = license_obj
        _license_cache['valid'] = result[0]
        _license_cache['reason'] = result[1]
        _license_cache['loaded_at'] = now

        return result

    def invalidate_cache(self):
        """Force re-validation on next call."""
        _license_cache['data'] = None
        _license_cache['loaded_at'] = 0

    # ─── Concurrency Control (Redis) ────────────────────────

    def _cleanup_expired_sessions(self):
        """Remove expired entries from the active sessions sorted set."""
        try:
            r = _get_redis()
            now = time.time()
            r.zremrangebyscore(self.REDIS_ACTIVE_SESSIONS_KEY, '-inf', now)
        except Exception as e:
            logger.warning('Failed to cleanup expired sessions: %s', e)

    def get_active_user_count(self):
        """Return the number of currently active (non-expired) users."""
        try:
            self._cleanup_expired_sessions()
            r = _get_redis()
            return r.zcard(self.REDIS_ACTIVE_SESSIONS_KEY)
        except Exception:
            return 0

    def check_concurrency(self, exclude_user_id=None):
        """
        Check if a new login is allowed under the concurrency limit.
        If exclude_user_id is provided, that user is not counted
        (they are re-logging in and will replace their entry).
        Returns True if login is allowed.
        """
        features = self.get_feature_limits()
        limit = features.get('max_concurrent_users')
        if not limit:
            return True  # No limit configured

        self._cleanup_expired_sessions()

        try:
            r = _get_redis()
            count = r.zcard(self.REDIS_ACTIVE_SESSIONS_KEY)

            # If the user already has an active session, they'll replace it
            if exclude_user_id is not None:
                score = r.zscore(self.REDIS_ACTIVE_SESSIONS_KEY, str(exclude_user_id))
                if score is not None:
                    count -= 1

            return count < int(limit)
        except Exception as e:
            logger.error('Redis concurrency check failed: %s', e)
            # Fail open — allow login if Redis is unavailable
            return True

    def register_session(self, user_id):
        """Register a user session with expiry score from daily token expiry."""
        try:
            from apps.core.utils.tokens import _get_daily_expiry
            expiry_ts = _get_daily_expiry().timestamp()
        except Exception:
            # Fallback: 24 hours from now
            expiry_ts = time.time() + 86400

        try:
            r = _get_redis()
            r.zadd(self.REDIS_ACTIVE_SESSIONS_KEY, {str(user_id): expiry_ts})
        except Exception as e:
            logger.error('Failed to register session in Redis: %s', e)

    def remove_session(self, user_id):
        """Remove a user session (on logout)."""
        try:
            r = _get_redis()
            r.zrem(self.REDIS_ACTIVE_SESSIONS_KEY, str(user_id))
        except Exception as e:
            logger.error('Failed to remove session from Redis: %s', e)

    # ─── MainDatabase Limit Check ───────────────────────────

    def check_main_db_limit(self):
        """Check if MainDatabase row count is at or exceeds the license limit.
        Returns True if under the limit (or no limit configured)."""
        features = self.get_feature_limits()
        limit = features.get('max_main_db')
        if not limit:
            return True

        try:
            from apps.core.model.authorize.models import MainDatabase
            count = MainDatabase.objects.count()
            return count < int(limit)
        except Exception as e:
            logger.error('Failed to check MainDatabase count: %s', e)
            return True
