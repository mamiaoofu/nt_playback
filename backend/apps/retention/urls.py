from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RetentionViewSet

router = DefaultRouter()
router.register(r'', RetentionViewSet, basename='retention')

urlpatterns = [
    path('logs/<int:pk>/download/', RetentionViewSet.as_view({'get': 'download_log'}), name='retention-log-download'),
    path('', include(router.urls)),
]
