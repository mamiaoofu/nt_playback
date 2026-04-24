from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Widen smb_password from varchar(64) to varchar(255) so it can hold
    plaintext passwords (not just 64-char SHA-256 hex digests).
    """

    dependencies = [
        ('home', '0004_fix_smb_password_plaintext'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filestorageconfig',
            name='smb_password',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='smb_password'),
        ),
    ]
