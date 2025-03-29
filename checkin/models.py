from django.db import models
from accounts.models import User, School
from django.utils import timezone
import datetime

# Create your models here.

# 打卡任务模型
class Checkin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_created_checkins', verbose_name='创建者')
    title = models.CharField(max_length=200, verbose_name='任务名称')
    time = models.CharField(max_length=100, verbose_name='时间要求', blank=True)
    description = models.TextField(verbose_name='描述', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '打卡任务'
        verbose_name_plural = '打卡任务'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
        
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'creator_name': self.user.username,
            'title': self.title,
            'time': self.time,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'checked_today': False,  # 默认今天未打卡
            'today_checkin_id': None  # 今天打卡记录的ID
        }


# 用户打卡记录
class UserCheckin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_checkins', verbose_name='用户')
    checkin_id = models.IntegerField(verbose_name='打卡任务ID')
    checkin_title = models.CharField(max_length=200, verbose_name='打卡任务名称', blank=True)
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name='打卡时间')
    # 新增日期字段，记录哪一天的打卡
    checkin_date = models.DateField(default=timezone.now, verbose_name='打卡日期')
    
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
            'checkin_date': self.checkin_date.strftime('%Y-%m-%d')
        }
