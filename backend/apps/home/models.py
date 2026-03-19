from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class FavoriteSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='User')
    favorite_name = models.CharField(max_length=30, verbose_name="favorite_name",null=False,blank=False )
    description = models.CharField(max_length=100,blank=True, verbose_name='Description')
    raw_data = models.JSONField( verbose_name='raw_data')  
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tb_favorite_search'
        verbose_name = 'favorite'
        ordering = ['favorite_name']

    def __str__(self):
        return f"{self.favorite_name}"
    
class ViewAudio(models.Model):
    interaction_id = models.IntegerField(verbose_name='interaction_id')
    database_name = models.TextField(verbose_name="database_name",null=False,blank=False )
    file_path = models.TextField(verbose_name="file_path",null=False,blank=False )
    duration_seconds = models.IntegerField(verbose_name='duration_seconds')
    call_direction = models.IntegerField(verbose_name='call_direction')
    phone_number = models.IntegerField(verbose_name='phone_number')
    extension = models.TextField(verbose_name="extension",null=False,blank=False )
    legacy_agent_id = models.TextField(verbose_name="legacy_agent_id",null=False,blank=False )
    agent_name = models.TextField(verbose_name="agent_name",null=False,blank=False )
    agent_group = models.TextField(verbose_name="agent_group",null=False,blank=False )
    first_name = models.TextField(verbose_name="first_name",null=False,blank=False )
    last_name = models.TextField(verbose_name="last_name",null=False,blank=False )
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        db_table = 'view_audio'
        
class SetColumnAudioRecord(models.Model):
    raw_data = models.TextField( verbose_name='raw_data',null=False,blank=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='User')
    status = models.IntegerField(verbose_name='status', default=1)  
    name = models.CharField( max_length=30,verbose_name='name',null=False,blank=False)
    description = models.CharField( max_length=100,verbose_name='description',null=True,blank=True)
    use = models.BooleanField( verbose_name='use',default=False)
    create_at = models.DateTimeField(auto_now_add=True) 
    update_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        db_table = 'tb_set_column_audio_record'
        verbose_name = 'Set Column Audio Record'

class ConfigKey(models.Model):
    type = models.CharField( max_length=255,verbose_name='type',null=False,blank=False)
    key_username = models.CharField( max_length=255,verbose_name='key_username',null=False,blank=False)
    key_password = models.CharField( max_length=255,verbose_name='key_password',null=False,blank=False)
    secret_key = models.CharField( max_length=255,verbose_name='secret_key',null=True,blank=True) 
    
    class Meta:
        db_table = 'config_key'
        verbose_name = 'config_key'

# class PlaybackLog(models.Model):
#     user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='User')
#     status = models.CharField(max_length=50, verbose_name='Status') # e.g., 'SUCCESS', 'FAIL_NOT_INSTALLED', 'FAIL_PLAYER_ERROR'
#     detail = models.TextField(verbose_name='Detail', blank=True)
#     ip_address = models.GenericIPAddressField(verbose_name='IP Address', null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'tb_playback_log'
#         verbose_name = 'Playback Log'
#         ordering = ['-created_at']