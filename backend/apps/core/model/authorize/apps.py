from django.apps import AppConfig


class AuthorizeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core.model.authorize'
    verbose_name = 'กำหนดรหัสสิทธิการทำงาน'

    def ready(self):
        import apps.core.utils.db_limit_signals  # noqa: F401
