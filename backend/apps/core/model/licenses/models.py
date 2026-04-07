from django.db import models

class License(models.Model):
    name = models.CharField(max_length=255, verbose_name='ชื่อแพ็กเกจ')
    duration_years = models.IntegerField(default=1, verbose_name='อายุการใช้งาน (ปี)')
    features = models.JSONField(default=dict, verbose_name='สิทธิ์การใช้งาน')  
    # เช่น {"menu1": True, "menu2": False}

    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tb_license'
        verbose_name = 'license'

    def __str__(self):
        return f"{self.name} ({self.duration_years} ปี)"


# class UserLicense(models.Model):
#     user_profile = models.ForeignKey("authorize.UserProfile", on_delete=models.CASCADE, verbose_name='User Profile')
#     license = models.ForeignKey(License, on_delete=models.CASCADE, verbose_name='License')
#     start_date = models.DateField(auto_now_add=True)
#     end_date = models.DateField(auto_now=True)

#     class Meta:
#         db_table = 'tb_userlicense'
#         verbose_name = 'user_license'

#     def __str__(self):
#         return f"{self.user_profile.user.username} - {self.license.name}"
