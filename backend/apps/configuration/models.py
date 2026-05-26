from django.contrib.auth.models import User
from django.db import models

class UserPermissionType(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name='Type Name')

    class Meta:
        db_table = 'tb_user_permission_type'

    def __str__(self):
        return self.name

class UserPermissionAction(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name='Action Name')

    class Meta:
        db_table = 'tb_user_permission_action'

    def __str__(self):
        return self.name

class UserPermission(models.Model):
    type = models.CharField(max_length=255, verbose_name='type')
    name = models.CharField(max_length=255, verbose_name='name')
    create_date = models.DateTimeField(auto_now_add=True, verbose_name='Start DateTime')
    update_date = models.DateTimeField(auto_now=True, verbose_name='End DateTime')
    
    class Meta:
        db_table = 'tb_user_permission'
        # ordering = ['type']

class UserPermissionDetail(models.Model):
    user_permission = models.ForeignKey(UserPermission, on_delete=models.CASCADE, verbose_name='User Permission')
    action = models.ForeignKey(UserPermissionAction, on_delete=models.CASCADE, verbose_name='Action')
    status = models.BooleanField(verbose_name='Status')
    type = models.ForeignKey(UserPermissionType, on_delete=models.CASCADE, verbose_name='type')
    default = models.BooleanField(verbose_name='Default')
    
    class Meta:
        db_table = 'tb_user_permission_detail'
        
    def __str__(self):
        return f"{self.user_permission.name} - {self.action.name}"