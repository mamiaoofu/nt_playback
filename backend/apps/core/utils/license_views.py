"""License info API views."""

from django.http import JsonResponse
from apps.core.utils.license_service import LicenseService


def api_license_info(request):
    """GET /api/license-info/ — Return sanitized license features.
    Does NOT expose fingerprint or signature."""
    svc = LicenseService()
    info = svc.get_license_info()
    if not info:
        return JsonResponse({'error': 'No license loaded.'}, status=404)

    info['active_users'] = svc.get_active_user_count()
    return JsonResponse(info)
