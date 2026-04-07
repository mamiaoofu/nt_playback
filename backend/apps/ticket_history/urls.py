from django.urls import path
from . import views

urlpatterns = [
	path('api/get/ticket-history/<str:type>/', views.ApiGetTicketHistory, name='ApiGetTicketHistory'),
	path('api/file-share-management/change-status/<int:user_id>/<str:type>/', views.ApiChangeFileShareStatus, name='ApiChangeFileShareStatus'),
	path('api/gen-form-ticket/', views.ApiGenFormTicket, name='ApiGenFormTicket'),
]

