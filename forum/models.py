from django.db import models
from accounts.models import School, User

# Create your models here.

# 论坛帖子模型
class Post(models.Model):
    STATUS_CHOICES = (
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    )
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='forum_posts', verbose_name='所属学校')
    title = models.CharField(max_length=200, verbose_name='标题')
    author = models.CharField(max_length=100, verbose_name='作者')
    content = models.TextField(verbose_name='内容', blank=True)
    time = models.DateTimeField(auto_now_add=True, verbose_name='发布时间')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name='发布用户', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='审核状态')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='reviewed_posts', verbose_name='审核人', null=True, blank=True)
    reviewed_time = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    reject_reason = models.TextField(verbose_name='拒绝原因', blank=True)
    
    class Meta:
        verbose_name = '论坛帖子'
        verbose_name_plural = '论坛帖子'
        ordering = ['-time']
        
    def __str__(self):
        return self.title
        
    def to_dict(self):
        return {
            'id': self.id,
            'school_id': self.school.id,
            'title': self.title,
            'author': self.author,
            'content': self.content,
            'time': self.time.strftime('%Y-%m-%d %H:%M'),
            'status': self.status,
            'status_display': self.get_status_display()
        }
