from django.contrib.auth.models import User
from django.db import models

class AudioFile(models.Model):
    file_path = models.CharField(max_length=512, verbose_name='File Path')
    file_name = models.CharField(max_length=255, verbose_name='File Name')
    file_type = models.CharField(max_length=20, blank=True, verbose_name='File Type')
    file_size = models.IntegerField(default=0, verbose_name='File Size')
    duration = models.DurationField(null=True, blank=True, verbose_name='Duration')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    
    class Meta:
        db_table = 'tb_audiofile'
        ordering = ['file_name']
        verbose_name = 'Audio File'

class AudioInfo(models.Model):
    main_db = models.ForeignKey('authorize.MainDatabase', on_delete=models.CASCADE,db_column='maindatabase_id', verbose_name='Main Database')
    customer = models.ForeignKey('customer.CustomerInfo', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Customer')
    audiofile = models.ForeignKey('audio.AudioFile', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Audio File')
    agent = models.ForeignKey('authorize.Agent', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Agent')
    call_direction = models.CharField(max_length=20, blank=True, verbose_name='Call Direction')
    extension = models.CharField(max_length=20, blank=True, verbose_name='Extension')
    customer_number = models.CharField(max_length=20, blank=True, verbose_name='Customer Number')
    start_datetime = models.DateTimeField(auto_now_add=True, verbose_name='Start DateTime')
    end_datetime = models.DateTimeField(auto_now=True, verbose_name='End DateTime')
    note = models.TextField(blank=True, verbose_name='Note', null=True)
    custom_field_1 = models.CharField(max_length=255, blank=True, verbose_name='Custom Field 1', null=True)
    
    
    class Meta:
        db_table = 'tb_audioinfo'
        ordering = ['-start_datetime']
        verbose_name = 'Audio Info'
        indexes = [
            models.Index(fields=['agent_id', 'start_datetime']),
        ]

