from django.urls import path
from . import views

urlpatterns = [
	path('api/ticket-history/get/<str:type>/', views.ApiGetTicketHistory, name='ApiGetTicketHistory'),
]

