from django.db import models
from accounts.models import User, School
from django.utils import timezone
import datetime
import json

# Create your models here.

# 打卡任务模型
class Checkin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_created_checkins', verbose_name='创建者')
    title = models.CharField(max_length=200, verbose_name='任务名称')
    time = models.CharField(max_length=100, verbose_name='时间要求', blank=True)
    description = models.TextField(verbose_name='描述', blank=True)
    
    # 目标时长（分钟）
    target_duration = models.IntegerField(default=0, verbose_name='目标时长(分钟)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '打卡任务'
        verbose_name_plural = '打卡任务'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
        
    def to_dict(self, current_user=None):
        # 检查今天是否已打卡（如果传入了current_user，使用current_user，否则使用创建者）
        user_for_check = current_user if current_user else self.user
        today = timezone.now().date()
        today_checkin = UserCheckin.objects.filter(
            user=user_for_check,
            checkin_id=self.id,
            checkin_date=today
        ).first()
        
        # 检查是否有活跃的打卡会话
        # 只有当今天的打卡还没有结束时间时，才返回活跃会话
        active_session = None
        if user_for_check and today_checkin and not today_checkin.end_time:
            active_session = CheckinSession.objects.filter(
                user=user_for_check,
                checkin_id=self.id,
                is_active=True
            ).first()
        
        return {
            'id': self.id,
            'user_id': self.user.id,
            'creator_name': self.user.username,
            'title': self.title,
            'time': self.time,
            'description': self.description,
            'target_duration': self.target_duration,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'checked_today': today_checkin is not None,
            'today_checkin_id': today_checkin.id if today_checkin else None,
            'today_checkin_data': today_checkin.to_dict() if today_checkin else None,
            'active_session': active_session.to_dict() if active_session else None,
            'is_creator': current_user.id == self.user.id if current_user else False
        }


# 打卡状态追踪模型（适用于学习类和运动类）
class CheckinSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    checkin_id = models.IntegerField(verbose_name='打卡任务ID')
    checkin_title = models.CharField(max_length=200, verbose_name='打卡任务名称')
    
    # 追踪状态
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    is_paused = models.BooleanField(default=False, verbose_name='是否暂停')
    
    # 时间记录
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    pause_time = models.DateTimeField(null=True, blank=True, verbose_name='暂停时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    total_paused_duration = models.IntegerField(default=0, verbose_name='总暂停时长(秒)')
    
    # 其他
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '打卡会话'
        verbose_name_plural = '打卡会话'
        ordering = ['-created_at']
        # 确保一个用户对一个打卡任务只能有一个活跃的会话
        unique_together = ('user', 'checkin_id', 'is_active')
        
    def __str__(self):
        status = "进行中" if self.is_active else "已结束"
        if self.is_paused:
            status = "暂停中"
        return f"{self.user.username} - {self.checkin_title} - {status}"
        
    def get_current_duration(self):
        """获取当前时长（秒）"""
        if not self.is_active:
            return 0
            
        now = timezone.now()
        if self.is_paused and self.pause_time:
            total_time = (self.pause_time - self.start_time).total_seconds()
        else:
            total_time = (now - self.start_time).total_seconds()
            
        return max(0, int(total_time - self.total_paused_duration))
        
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'checkin_id': self.checkin_id,
            'checkin_title': self.checkin_title,
            'is_active': self.is_active,
            'is_paused': self.is_paused,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'pause_time': self.pause_time.strftime('%Y-%m-%d %H:%M:%S') if self.pause_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'total_paused_duration': self.total_paused_duration,
            'current_duration': self.get_current_duration(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


# 用户打卡记录
class UserCheckin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_checkins', verbose_name='用户')
    checkin_id = models.IntegerField(verbose_name='打卡任务ID')
    checkin_title = models.CharField(max_length=200, verbose_name='打卡任务名称', blank=True)
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name='打卡时间')
    # 新增日期字段，记录哪一天的打卡
    checkin_date = models.DateField(default=timezone.now, verbose_name='打卡日期')
    
    # 任务完成数据
    duration = models.IntegerField(default=0, verbose_name='完成时长(秒)')  # 学习类和运动类都使用这个字段
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    
    # 通用数据
    notes = models.TextField(blank=True, verbose_name='打卡备注')
    shared_to_community = models.BooleanField(default=False, verbose_name='是否已分享到社区')
    
    class Meta:
        verbose_name = '用户打卡记录'
        verbose_name_plural = '用户打卡记录'
        # 一个用户对一个打卡任务在同一天只能打卡一次
        unique_together = ('user', 'checkin_id', 'checkin_date')
        ordering = ['-checked_at']
        
    def __str__(self):
        checkin_name = self.checkin_title 
        return f"{self.user.username} - {checkin_name} - {self.checkin_date}"

        
    def to_dict(self):
        checkin_id = self.checkin_id 
        checkin_title = self.checkin_title 
        
        return {
            'id': self.id,
            'user_id': self.user.id,
            'username': self.user.username,
            'checkin_id': checkin_id,
            'checkin_title': checkin_title,
            'checked_at': self.checked_at.strftime('%Y-%m-%d %H:%M:%S'),
            'checkin_date': self.checkin_date.strftime('%Y-%m-%d'),
            # 完成数据
            'duration': self.duration,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            # 备注
            'notes': self.notes
        }
