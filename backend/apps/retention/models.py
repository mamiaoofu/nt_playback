import uuid
from django.db import models

class RetentionTask(models.Model):
    TASK_TYPES = [
        ('MANUAL', 'Manual'),
        ('AUTO_EXECUTION', 'Auto Execution')
    ]
    STATUS_CHOICES = [
        ('READY', 'Ready'),
        ('RUNNING', 'Running'),
        ('STOPPED', 'Stopped'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('RESTORED', 'Restored')
    ]
    
    id = models.AutoField(primary_key=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    delete_option = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RUNNING')
    index_count = models.IntegerField(default=0)
    time_period = models.CharField(max_length=100, blank=True, null=True)
    user_create = models.CharField(max_length=100)
    executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'retention_task'
        ordering = ['-created_at']

class RetentionLog(models.Model):
    id = models.AutoField(primary_key=True)
    task_type = models.CharField(max_length=20)
    delete_option = models.CharField(max_length=50)
    index_count = models.IntegerField(default=0)
    time_period = models.CharField(max_length=100, blank=True, null=True)
    user_create = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    file_log_path = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='SUCCESS')

    class Meta:
        db_table = 'retention_log'
        ordering = ['-created_at']

class AutoRetentionConfig(models.Model):
    # Singleton model
    retention_type = models.CharField(max_length=20, default='OLDER_THAN')
    older_than_type = models.CharField(max_length=20, default='RELATIVE')
    retention_period = models.CharField(max_length=10, blank=True, null=True) # relative: 6M, 1Y, 5Y, 10Y
    older_than_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_once = models.BooleanField(default=False)
    is_recurrence = models.BooleanField(default=True)
    
    how_often = models.CharField(max_length=20, default='monthly')
    what_day = models.CharField(max_length=20, null=True, blank=True)
    execution_time = models.TimeField(blank=True, null=True)
    
    delete_option = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    user_update = models.CharField(max_length=100, blank=True, null=True)
    permanent_delete_value = models.IntegerField(default=30)
    permanent_delete_unit = models.CharField(max_length=10, default='days')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'auto_retention_config'

    def save(self, *args, **kwargs):
        self.pk = 1
        super(AutoRetentionConfig, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
