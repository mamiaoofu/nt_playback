from django.urls import path
from . import views

urlpatterns = [
    path('api/setting/get/column-audio-record/', views.ApiGetColumnAudioRecord, name='ApiGetColumnAudioRecord'),
    path('api/setting/save/column-audio-record/', views.ApiSaveColumnAudioRecord, name='ApiSaveColumnAudioRecord'),
    path('api/setting/active-directory/', views.ApiActiveDirectorySetting, name='ApiActiveDirectorySetting'),
    path('api/setting/network-share/', views.ApiNetworkShareSetting, name='ApiNetworkShareSetting'),
    path('api/setting/mail/', views.ApiMailSetting, name='ApiMailSetting'),
]