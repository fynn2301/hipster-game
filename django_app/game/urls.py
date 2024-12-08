from django.urls import path
from . import views

urlpatterns = [
    path('', views.connect_to_spotify, name='spotify_connect'),
    path('spotify_callback/', views.spotify_callback, name='spotify_callback'),
    path('select_settings/', views.select_settings, name='select_settings'),
    path('start_cards/', views.start_cards, name='start_cards'),
    path('music_player/', views.music_player, name='music_player'),
    path('store_device_id/', views.store_device_id, name='store_device_id'),
]
