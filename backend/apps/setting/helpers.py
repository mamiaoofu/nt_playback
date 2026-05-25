from apps.setting.models import ActiveDirectorySetting, NetworkShareSetting, MailSetting
from django.conf import settings

def get_ad_settings():
    try:
        config = ActiveDirectorySetting.objects.first()
    except Exception:
        config = None

    if config:
        return {
            'AD_SERVER_URI': config.server_uri,
            'AD_DOMAIN': config.domain,
            'AD_BASE_DN': config.base_dn,
            'AD_BIND_USER': config.bind_user,
            'AD_BIND_PASSWORD': config.get_password(),
        }
    return {
        'AD_SERVER_URI': getattr(settings, 'AD_SERVER_URI', None),
        'AD_DOMAIN': getattr(settings, 'AD_DOMAIN', None),
        'AD_BASE_DN': getattr(settings, 'AD_BASE_DN', None),
        'AD_BIND_USER': getattr(settings, 'AD_BIND_USER', None),
        'AD_BIND_PASSWORD': getattr(settings, 'AD_BIND_PASSWORD', None),
    }

def get_network_share_settings():
    try:
        config = NetworkShareSetting.objects.first()
    except Exception:
        config = None

    if config:
        return {
            'NT_SHARE_HOST': config.host,
            'NT_SHARE_SHARE': config.share,
            'NT_SHARE_USER': config.user,
            'NT_SHARE_PASS': config.get_password(),
            'NT_SMB_CLIENT_NAME': config.client_name,
        }
    return {
        'NT_SHARE_HOST': getattr(settings, 'NT_SHARE_HOST', None),
        'NT_SHARE_SHARE': getattr(settings, 'NT_SHARE_SHARE', None),
        'NT_SHARE_USER': getattr(settings, 'NT_SHARE_USER', None),
        'NT_SHARE_PASS': getattr(settings, 'NT_SHARE_PASS', None),
        'NT_SMB_CLIENT_NAME': getattr(settings, 'NT_SMB_CLIENT_NAME', 'nt_playback'),
    }

def get_mail_settings():
    try:
        config = MailSetting.objects.first()
    except Exception:
        config = None

    if config:
        return {
            'EMAIL_BACKEND': config.backend,
            'DEFAULT_FROM_EMAIL': config.from_email,
            'EMAIL_USE_TLS': config.use_tls,
            'EMAIL_HOST_USER': config.host_user,
            'EMAIL_HOST_PASSWORD': config.get_password(),
            'EMAIL_HOST': config.host,
            'EMAIL_PORT': config.port,
        }
    return {
        'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', None),
        'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', True),
        'EMAIL_HOST_USER': getattr(settings, 'EMAIL_HOST_USER', None),
        'EMAIL_HOST_PASSWORD': getattr(settings, 'EMAIL_HOST_PASSWORD', None),
        'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', None),
        'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 587),
    }
