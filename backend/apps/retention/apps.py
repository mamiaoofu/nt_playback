from django.apps import AppConfig


class RetentionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.retention'

    def ready(self):
        import os
        import sys
        print("RetentionConfig ready() called!")
        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'check', 'showmigrations']):
            print("Bypassing scheduler start for management commands.")
            return
        is_runserver = 'runserver' in sys.argv
        is_noreload = '--noreload' in sys.argv
        if not is_runserver or os.environ.get('RUN_MAIN', None) == 'true' or is_noreload:
            from . import scheduler
            scheduler.start()
