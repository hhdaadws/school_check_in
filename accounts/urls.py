from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # API端点
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('send-verification-code/', views.send_verification_code, name='send_verification_code'),
    
    # 前端页面
    path('', views.home_page, name='home_page'),  # 主页
    path('auth/', views.auth_page, name='auth_page'),
] 