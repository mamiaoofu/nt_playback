from django.db import migrations


def store_plaintext_password(apps, schema_editor):
    """
    Replace the SHA-256 hash in smb_password with the actual plaintext password.
    The plaintext is needed so the installer can store it in Windows Credential
    Manager for SMB (net use) authentication.
    Security: the API endpoint that returns this value is protected by
    INSTALLER_SECRET_KEY, so end users never see the password.
    """
    FileStorageConfig = apps.get_model('home', 'FileStorageConfig')
    config = FileStorageConfig.objects.filter(is_active=1).first()
    if not config:
        config = FileStorageConfig.objects.first()
    if config:
        config.smb_password = 'Bl@ze389'
        config.save()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_seed_smb_credentials'),
    ]

    operations = [
        migrations.RunPython(store_plaintext_password, migrations.RunPython.noop),
    ]
