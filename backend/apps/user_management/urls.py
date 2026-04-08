from django.urls import path
from . import views 

urlpatterns = [
    path('api/get/user/', views.ApiGetUser, name='ApiGetUser'),
    path('api/get/user-all/<str:type>/', views.ApiGetUserAll, name='ApiGetUserAll'),
    
    path('api/user-management/change-status/<int:user_id>/', views.ApiChangeUserStatus, name='ApiChangeUserStatus'),
    path('api/add-user/get-all-roles-permissions/', views.ApiGetAllRolesPermissions, name='ApiGetAllRolesPermissions'),
    path('api/user-management/get-profile/<int:user_id>/', views.ApiGetUSerProfile, name='ApiGetUSerProfile'),
    path('api/add-user/check-username/', views.ApiCheckUsername, name='ApiCheckUsername'),
    path('api/add-user/', views.ApiSaveUser, name='ApiSaveUser'),
    path('api/edit-user/<int:user_id>/', views.ApiSaveUser, name='ApiEditUser'),
    path('api/user-management/delete-user/<int:user_id>/', views.ApiDeleteUser, name='ApiDeleteUser'),
    path('api/user-management/reset-password/<int:user_id>/', views.ApiResetPassword, name='ApiResetPassword'),
    path('api/change-password/', views.ApiChangePassword, name='ApiChangePassword'),
]