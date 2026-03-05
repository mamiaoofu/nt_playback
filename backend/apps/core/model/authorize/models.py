from django.contrib.auth.models import User
from django.db import models
# from apps.model_center.audio.models import AudioFile

class MainDatabase(models.Model):
    database_name = models.CharField(max_length=255, unique=True, verbose_name='Database Name')
    description = models.TextField(blank=True, verbose_name='Description')
    status = models.BooleanField(verbose_name='status')
    
    class Meta:
        # db_table = 'tb_maindatabase_nice'
        db_table = 'tb_maindatabase'
        
        ordering = ['database_name']
        verbose_name = 'Main Database'

    def __str__(self):
        return self.database_name


class UserAuth(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    maindatabase = models.ForeignKey(MainDatabase, on_delete=models.CASCADE)
    allow = models.BooleanField()

    user_permission = models.ForeignKey(
        'configuration.UserPermission',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='user_permisson_id',  
        verbose_name='User Permission'
    )

    class Meta:
        db_table = 'tb_userauth'

        
class UserLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='User',null=True, blank=True)
    action = models.CharField(max_length=255, verbose_name='Action')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp')
    detail = models.TextField(blank=True, verbose_name='Detail')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP Address')
    # audiofile = models.ForeignKey('audio.AudioFile', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Audio File')
    client_type = models.CharField(max_length=255, verbose_name='บราวเซอร์ผู้ใช้')
    status = models.CharField(max_length=50, verbose_name='status')
    
    class Meta:
        db_table = 'tb_userlog'
        ordering = ['-timestamp']
        verbose_name = 'User Log'

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"
    
class SetAudio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='User')
    audio_path = models.CharField(max_length=255, verbose_name='audio_path')
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    client_token  = models.CharField(max_length=255, verbose_name='client_token')
    selected = models.BooleanField(verbose_name='selected')
    
    class Meta:
        db_table = 'tb_set_audio'
        ordering = ['-selected']
        verbose_name = 'set_audio'

    def __str__(self):
        return f"{self.audio_path}"
    
class Department(models.Model):
    name_th = models.CharField(max_length=255, verbose_name='name_th')
    name_en = models.CharField(max_length=255, verbose_name='name_en')

    class Meta:
        db_table = 'tb_department'
        verbose_name = 'department'

    def __str__(self):
        return f"{self.name_en}"
    
class AgentGroup(models.Model):
    group_name = models.CharField(max_length=255, verbose_name='Agent Group Name')
    description = models.TextField(blank=True, verbose_name='Description')
    status = models.IntegerField(verbose_name='status')

    class Meta:
        db_table = 't_group'
        ordering = ['group_name']
        verbose_name = 'Agent Group'
        

    def __str__(self):
        return self.group_name
    
class Agent(models.Model):
    agent_code = models.CharField(max_length=50, unique=True, verbose_name='Agent ID')
    first_name = models.CharField(max_length=50, verbose_name='first_name')
    last_name = models.CharField(max_length=50, verbose_name='last_name')
    agent_group_id = models.ForeignKey(AgentGroup, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='AgentGroup', db_column='agent_group_id' )
    note = models.TextField(blank=True, verbose_name='Note')

    class Meta:
        db_table = 'tb_agent'
        ordering = ['first_name']
        verbose_name = 'Agent'
        managed = False
        

    def __str__(self):
        return f"{self.agent_code} - {self.first_name}"
    
class UserGroup(models.Model):
    group_name = models.CharField(max_length=255, verbose_name='User Group Name')
    description = models.TextField(blank=True, verbose_name='Description')
    status = models.IntegerField(verbose_name='status')
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tb_user_group'
        ordering = ['create_at']
        verbose_name = 'User Group'
        
    def __str__(self):
        return self.group_name
    
class UserTeam(models.Model):
    name = models.CharField(max_length=255, verbose_name='User Group Name')
    user_group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, verbose_name='user_group_id',db_column='user_group_id')
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    maindatabase = models.TextField(verbose_name='maindatabase',db_column='maindatabase_id')
    status = models.IntegerField(verbose_name='status',default=1)

    class Meta:
        db_table = 'tb_user_team'
        ordering = ['user_group']
        verbose_name = 'User team'
        
    def __str__(self):
        return self.name
    
class UserProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='User')
    team = models.ForeignKey(UserTeam, on_delete=models.CASCADE, verbose_name='team',db_column='team_id' )
    user_code = models.CharField(max_length=255, verbose_name='user_code')
    phone = models.CharField(max_length=255, verbose_name='user_code')
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    session_token = models.CharField(max_length=255, verbose_name='session_token') 
    privilege_history = models.BooleanField(verbose_name='สิทธิดูประวัติผู้ใช้')

    class Meta:
        ordering = ['user__username']
        db_table = 'tb_userprofile'
        verbose_name = 'userprofile'

    def __str__(self):
        return f"{self.user_code} - {self.user.first_name} {self.user.last_name}"
        
class UserFileShare(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='user_id', db_column='user_id', related_name='file_shares')
    type = models.CharField(max_length=255, verbose_name='type')
    code = models.CharField(max_length=255, verbose_name='code')
    email = models.TextField(verbose_name='email')
    audiofile_id = models.TextField(verbose_name='audiofile_id')
    start_at = models.DateTimeField(verbose_name='start_at')
    expire_at = models.DateTimeField(verbose_name='expire_at')
    status = models.BooleanField(verbose_name='status',default=True)
    # phone = models.CharField(max_length=255, verbose_name='phone')
    view = models.BooleanField(verbose_name='view',default=False)
    dowload = models.BooleanField(verbose_name='dowload',default=False)
    create_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='create_by', db_column='create_by',related_name='created_file_shares')
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tb_file_share'
        ordering = ['-update_at']
        verbose_name = 'User File Share'
