"""
Migration: encrypt the plaintext smb_password already in the database using
AES-256-GCM (via apps.core.utils.smb_crypto).

Requires SMB_ENCRYPTION_KEY to be set in the environment before running.
Run:
    SMB_ENCRYPTION_KEY=<key> python manage.py migrate
"""
from django.db import migrations


def encrypt_existing_passwords(apps, schema_editor):
    from apps.core.utils.smb_crypto import encrypt_smb_password, is_encrypted
    FileStorageConfig = apps.get_model('home', 'FileStorageConfig')
    for config in FileStorageConfig.objects.exclude(smb_password='').filter(smb_password__isnull=False):
        if not is_encrypted(config.smb_password):
            config.smb_password = encrypt_smb_password(config.smb_password)
            config.save(update_fields=['smb_password'])


def decrypt_existing_passwords(apps, schema_editor):
    """Reverse: decrypt back to plaintext (for rollback)."""
    from apps.core.utils.smb_crypto import decrypt_smb_password, is_encrypted
    FileStorageConfig = apps.get_model('home', 'FileStorageConfig')
    for config in FileStorageConfig.objects.exclude(smb_password='').filter(smb_password__isnull=False):
        if is_encrypted(config.smb_password):
            config.smb_password = decrypt_smb_password(config.smb_password)
            config.save(update_fields=['smb_password'])


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_filestorageconfig_smb_password_widen'),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_passwords, decrypt_existing_passwords),
    ]
