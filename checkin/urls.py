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
    
    # 更新学习时长
    path('checkins/<int:checkin_id>/study/update/', views.update_study_duration, name='update_study_duration'),
    
    # 更新运动轨迹
    path('checkins/<int:checkin_id>/sport/update/', views.update_sport_trajectory, name='update_sport_trajectory'),
    
    # 打卡会话管理
    path('checkins/<int:checkin_id>/session/pause/', views.pause_checkin_session, name='pause_checkin_session'),
    path('checkins/<int:checkin_id>/session/resume/', views.resume_checkin_session, name='resume_checkin_session'),
    path('checkins/<int:checkin_id>/session/update/', views.update_checkin_session, name='update_checkin_session'),
    path('checkins/<int:checkin_id>/session/end/', views.end_checkin_session, name='end_checkin_session'),
    
    # 删除打卡任务
    path('checkins/<int:checkin_id>/delete/', views.delete_checkin, name='delete_checkin'),
    
    # 分享打卡到社区
    path('checkins/records/<int:checkin_record_id>/share/', views.share_to_community, name='share_to_community'),
] 