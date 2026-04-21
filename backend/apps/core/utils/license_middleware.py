"""
License enforcement middleware.

Validates the license on every request (using cached result) and blocks
the system if the license is missing, invalid, expired, or fingerprint
doesn't match.
"""

import logging

from django.http import JsonResponse

from apps.core.utils.license_service import LicenseService

logger = logging.getLogger(__name__)

# Paths that are exempt from license enforcement
EXEMPT_PATHS = (
    '/login/',
    '/api/get/csrf/',
    '/api/license-info/',
    '/api/token/refresh/',
    '/api/token/refresh_from_cookie/',
    '/api/logout/',
    '/admin/',
    '/static/',
    '/media/',
)

LICENSE_ERROR_MESSAGES = {
    'no_license': 'No license file found. Please deploy a valid license.',
    'invalid_signature': 'License signature is invalid. The license file may have been tampered with.',
    'fingerprint_mismatch': 'License fingerprint does not match this machine.',
    'expired': 'License has expired. Please contact your administrator.',
}


class LicenseEnforcementMiddleware:
    """
    Django middleware that enforces license validation on every request.

    - Exempt paths (login, csrf, static, etc.) are allowed through.
    - On valid license: injects request.license_features dict.
    - On invalid license: returns 403 JSON response with reason.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.license_service = LicenseService()

    def __call__(self, request):
        # Skip exempt paths
        path = request.path
        if any(path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        # Validate license (cached)
        is_valid, reason = self.license_service.validate_full()

        if not is_valid:
            msg = LICENSE_ERROR_MESSAGES.get(reason, 'License validation failed.')
            logger.warning('License blocked request to %s: %s', path, reason)
            return JsonResponse({
                'error': msg,
                'license_status': reason,
            }, status=403)

        # Inject license features into request for downstream views
        request.license_features = self.license_service.get_feature_limits()

        return self.get_response(request)
