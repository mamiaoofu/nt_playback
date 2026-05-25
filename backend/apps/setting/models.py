from django.db import models
from apps.core.utils.smb_crypto import encrypt_smb_password, decrypt_smb_password, is_encrypted

class ActiveDirectorySetting(models.Model):
    server_uri = models.CharField(max_length=255, default='ldap://192.168.1.8', verbose_name='AD Server URI')
    domain = models.CharField(max_length=255, default='nichetel.local', verbose_name='AD Domain')
    base_dn = models.CharField(max_length=255, default='cn=Users,dc=nichetel,dc=local', verbose_name='AD Base DN')
    bind_user = models.CharField(max_length=255, default='administrator', verbose_name='AD Bind User')
    bind_password = models.CharField(max_length=255, blank=True, null=True, verbose_name='AD Bind Password (Encrypted)')

    class Meta:
        db_table = 'tb_setting_active_directory'
        verbose_name = 'Active Directory Setting'

    def get_password(self):
        if self.bind_password and is_encrypted(self.bind_password):
            try:
                return decrypt_smb_password(self.bind_password)
            except Exception:
                return self.bind_password
        return self.bind_password

    def set_password(self, raw_password):
        if raw_password:
            self.bind_password = encrypt_smb_password(raw_password)
        else:
            self.bind_password = None

    def __str__(self):
        return f"AD Config: {self.domain}"


class NetworkShareSetting(models.Model):
    host = models.CharField(max_length=255, default='192.168.1.90', verbose_name='SMB Share Host')
    share = models.CharField(max_length=255, default='Users', verbose_name='SMB Share Name')
    user = models.CharField(max_length=255, default='Administrator', verbose_name='SMB Share User')
    password = models.CharField(max_length=255, blank=True, null=True, verbose_name='SMB Share Password (Encrypted)')
    client_name = models.CharField(max_length=255, default='nt_playback', verbose_name='SMB Client Name')

    class Meta:
        db_table = 'tb_setting_network_share'
        verbose_name = 'Network Share Setting'

    def get_password(self):
        if self.password and is_encrypted(self.password):
            try:
                return decrypt_smb_password(self.password)
            except Exception:
                return self.password
        return self.password

    def set_password(self, raw_password):
        if raw_password:
            self.password = encrypt_smb_password(raw_password)
        else:
            self.password = None

    def __str__(self):
        return f"Network Share Config: {self.host}"


class MailSetting(models.Model):
    backend = models.CharField(
        max_length=255, 
        default='django.core.mail.backends.smtp.EmailBackend', 
        verbose_name='Email Backend'
    )
    from_email = models.CharField(max_length=255, default='nichetelcomm@gmail.com', verbose_name='Default From Email')
    use_tls = models.BooleanField(default=True, verbose_name='Use TLS')
    host_user = models.CharField(max_length=255, default='nichetelcomm@gmail.com', verbose_name='Email Host User')
    host_password = models.CharField(max_length=255, blank=True, null=True, verbose_name='Email Host Password (Encrypted)')
    host = models.CharField(max_length=255, default='smtp.gmail.com', verbose_name='Email Host')
    port = models.IntegerField(default=587, verbose_name='Email Port')

    class Meta:
        db_table = 'tb_setting_mail'
        verbose_name = 'Mail Setting'

    def get_password(self):
        if self.host_password and is_encrypted(self.host_password):
            try:
                return decrypt_smb_password(self.host_password)
            except Exception:
                return self.host_password
        return self.host_password

    def set_password(self, raw_password):
        if raw_password:
            self.host_password = encrypt_smb_password(raw_password)
        else:
            self.host_password = None

    def __str__(self):
        return f"Mail Config: {self.host_user} ({self.host})"
