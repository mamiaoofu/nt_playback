import logging
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)

class DbEmailBackend(SmtpEmailBackend):
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None,
                 **kwargs):
        from apps.setting.models import MailSetting
        try:
            config = MailSetting.objects.first()
        except Exception:
            config = None

        if config:
            if host is None:
                host = config.host
            if port is None:
                port = config.port
            if username is None:
                username = config.host_user
            if password is None:
                try:
                    password = config.get_password()
                except Exception as exc:
                    logger.warning(
                        'DbEmailBackend could not decrypt mail password from DB; falling back to settings.EMAIL_HOST_PASSWORD: %s',
                        exc
                    )
                    password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            if use_tls is None:
                use_tls = config.use_tls
        else:
            if host is None:
                host = getattr(settings, 'EMAIL_HOST', None)
            if port is None:
                port = getattr(settings, 'EMAIL_PORT', 587)
            if username is None:
                username = getattr(settings, 'EMAIL_HOST_USER', None)
            if password is None:
                password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            if use_tls is None:
                use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        
        super().__init__(host=host, port=port, username=username, password=password,
                         use_tls=use_tls, fail_silently=fail_silently, use_ssl=use_ssl, timeout=timeout,
                         ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile, **kwargs)
