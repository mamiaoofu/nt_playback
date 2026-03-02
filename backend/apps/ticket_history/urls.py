from django.urls import path
from . import views

urlpatterns = [
	path('api/get/ticket-history/', views.ApiGetTicketHistory, name='ApiGetTicketHistory'),
]

