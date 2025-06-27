from django.urls import path
from . import views
from django.shortcuts import redirect


app_name = 'accounts'

urlpatterns = [
    # API端点
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('send-verification-code/', views.send_verification_code, name='send_verification_code'),
    path('update-email/', views.update_email, name='update_email'),
   
    # 兴趣标签相关API
    path('interests/tags/', views.get_interest_tags, name='get_interest_tags'),
    path('interests/select/', views.select_interests, name='select_interests'),
    path('interests/skip/', views.skip_interests, name='skip_interests'),
    path('interests/user/', views.get_user_interests, name='get_user_interests'),
   
    # 前端页面
    path('', views.home_page, name='home_page'),  # 主页
    path('auth/', views.auth_page, name='auth_page'),
    path('interests/', views.interests_page, name='interests_page'),
    # path('logout/', views.logout, name='logout'),
    # path('verify-code/', views.verify_code, name='verify_code'),

] 