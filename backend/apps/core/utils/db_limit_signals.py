"""
Database row limit enforcement signals.

Listens to pre_save and pre_delete on MainDatabase to enforce the
license-defined max_main_db limit.
"""

import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver

from apps.core.model.authorize.models import MainDatabase

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=MainDatabase)
def check_main_db_insert_limit(sender, instance, **kwargs):
    """Block INSERT if MainDatabase rows are at the license limit."""
    if instance.pk is not None:
        return  # UPDATE, not INSERT — always allowed

    try:
        from apps.core.utils.license_service import LicenseService
        svc = LicenseService()
        features = svc.get_feature_limits()
        limit = features.get('max_main_db')
        if not limit:
            return  # No limit configured

        count = MainDatabase.objects.count()
        if count >= int(limit):
            raise ValidationError(
                f'MainDatabase row limit reached ({limit}). '
                f'Cannot add more databases per your license.'
            )
    except ValidationError:
        raise
    except Exception as e:
        logger.error('Error checking MainDatabase insert limit: %s', e)


@receiver(pre_delete, sender=MainDatabase)
def check_main_db_delete_limit(sender, instance, **kwargs):
    """Block DELETE if MainDatabase rows are at the license limit
    (prevent reducing below the locked count)."""
    try:
        from apps.core.utils.license_service import LicenseService
        svc = LicenseService()
        features = svc.get_feature_limits()
        limit = features.get('max_main_db')
        if not limit:
            return  # No limit configured

        count = MainDatabase.objects.count()
        if count <= int(limit):
            raise ValidationError(
                f'Cannot delete: MainDatabase is at the license limit ({limit}). '
                f'Deletion is not allowed.'
            )
    except ValidationError:
        raise
    except Exception as e:
        logger.error('Error checking MainDatabase delete limit: %s', e)
