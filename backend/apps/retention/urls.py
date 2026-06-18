from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RetentionViewSet

router = DefaultRouter()
router.register(r'', RetentionViewSet, basename='retention')

urlpatterns = [
    path('', include(router.urls)),
]
