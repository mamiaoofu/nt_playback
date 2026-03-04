from django.urls import path
from . import views

urlpatterns = [
	path('api/audio/list/', views.ApiGetAudioList, name='ApiGetAudioList'),
	path('api/home/index/', views.ApiIndexHome, name='ApiIndexHome'),
	path('api/home/add/my-favorite-search/', views.ApiSaveMyFavoriteSearch, name='ApiAddMyFavoriteSearch'),
	path('api/home/check/my-favorite-search/', views.ApiCheckMyFavoriteName, name='ApiCheckMyFavoriteName'),
	path('api/home/edit/my-favorite-search/<int:myfavoriteId>/', views.ApiIndexHome, name='ApiEditMyFavoriteSearch'),
	path('api/log/play-audio/', views.ApiLogPlayAudio, name='ApiLogPlayAudio'),
	path('api/get/credentials/', views.ApiGetCredentials, name='ApiGetCredentials'),
    path('api/log/save-file/', views.ApiLogSaveFile, name='ApiLogSaveFile'),
    path('api/get/csrf/', views.ApiGetCsrfToken, name='ApiGetCsrfToken'),
	path('api/my-permissions/', views.ApiGetMyPermissions, name='ApiGetMyPermissions'),
	path('api/send-share-email/', views.ApiSendShareEmail, name='ApiSendShareEmail'),
	path('api/file-share/create/', views.ApiCreateFileShare, name='ApiCreateFileShare'),
]

