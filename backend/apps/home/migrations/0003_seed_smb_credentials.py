import hashlib
from django.db import migrations


def set_smb_credentials(apps, schema_editor):
    FileStorageConfig = apps.get_model('home', 'FileStorageConfig')
    config = FileStorageConfig.objects.filter(is_active=1).first()
    if not config:
        config = FileStorageConfig.objects.first()
    if config:
        config.smb_username = 'Administrator'
        config.smb_password = hashlib.sha256('Bl@ze389'.encode()).hexdigest()
        config.save()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0002_filestorageconfig'),
    ]

    operations = [
        migrations.RunPython(set_smb_credentials, migrations.RunPython.noop),
    ]
