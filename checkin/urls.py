from django.urls import path
from . import views

app_name = 'checkin'

urlpatterns = [
    # 获取打卡任务列表
    path('checkins/', views.get_checkins, name='get_checkins'),
    
    # 获取社区打卡
    path('community/', views.get_community_checkins, name='get_community_checkins'),
    
    # 创建打卡任务
    path('checkins/create/', views.create_checkin, name='create_checkin'),
    
    # 执行打卡操作
    path('checkins/<int:checkin_id>/check/', views.do_checkin, name='do_checkin'),
    
    # 删除打卡任务
    path('checkins/<int:checkin_id>/delete/', views.delete_checkin, name='delete_checkin'),
] 