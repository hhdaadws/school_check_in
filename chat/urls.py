from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('room/<int:school_id>/', views.chat_room, name='chat_room'),
    path('room/data/<int:school_id>/', views.chat_room_data, name='chat_room_data'),
    path('rooms/', views.chat_rooms, name='chat_rooms'),
    path('history/<str:room_name>/', views.chat_history, name='chat_history'),
    path('clear/<str:room_name>/', views.clear_chat_messages, name='clear_chat_messages'),
    path('send/<str:room_name>/', views.send_message, name='send_message'),
] 