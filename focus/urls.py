from django.urls import path
from . import views

urlpatterns = [
    # 专注设置
    path('settings/', views.get_focus_settings, name='get_focus_settings'),
    path('settings/update/', views.update_focus_settings, name='update_focus_settings'),
    
    # 专注会话
    path('session/start/', views.start_focus_session, name='start_focus_session'),
    path('session/end/', views.end_focus_session, name='end_focus_session'),
    path('session/active/', views.get_active_session, name='get_active_session'),
    
    # 历史和统计
    path('history/', views.get_focus_history, name='get_focus_history'),
    path('stats/', views.get_focus_stats, name='get_focus_stats'),
] 