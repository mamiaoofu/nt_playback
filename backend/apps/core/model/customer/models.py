from django.db import models

class CustomerContact(models.Model):
    phone_number = models.CharField(max_length=20, verbose_name='Phone Number')
    email = models.EmailField(blank=True, verbose_name='Email')
    address = models.TextField(blank=True, verbose_name='Address')
    
    class Meta:
        db_table = 'tb_customercontact'
        ordering = ['phone_number']
        verbose_name = 'Customer Contact'

class CustomerInfo(models.Model):
    name = models.CharField(max_length=255, verbose_name='Customer Name')
    customercontact = models.ForeignKey(CustomerContact, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Customer Contact')
    company = models.CharField(max_length=255, blank=True, verbose_name='Company')
    note = models.TextField(blank=True, verbose_name='Note')
    
    class Meta:
        db_table = 'tb_customerinfo'
        ordering = ['name']
        verbose_name = 'Customer Info'
    
    def __str__(self):
        return self.name
        