from django.db import models
from accounts.models import School, User
import json

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
    auto_approved = models.BooleanField(default=False, verbose_name='自动审核通过')
    moderation_result = models.CharField(max_length=50, blank=True, verbose_name='审核结果详情')
    
    class Meta:
        verbose_name = '论坛帖子'
        verbose_name_plural = '论坛帖子'
        ordering = ['-time']
        
    def __str__(self):
        return self.title
        
    def to_dict(self, user=None):
        return {
            'id': self.id,
            'school_id': self.school.id,
            'title': self.title,
            'author': self.author,
            'content': self.content,
            'time': self.time.strftime('%Y-%m-%d %H:%M'),
            'status': self.status,
            'status_display': self.get_status_display(),
            'tags': [tag.to_dict() for tag in self.post_tags.all()],
            'likes_count': self.likes.count(),
            'comments_count': self.comments.filter(is_deleted=False).count(),
            'user_liked': self.likes.filter(user=user).exists() if user else False,
            'recent_comments': [comment.to_dict() for comment in self.comments.filter(is_deleted=False)[:3]]
        }

# 帖子标签关联模型
class PostTag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_tags', verbose_name="帖子")
    interest_tag = models.ForeignKey('accounts.InterestTag', on_delete=models.CASCADE, verbose_name="兴趣标签")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")
    
    class Meta:
        verbose_name = "帖子标签"
        verbose_name_plural = "帖子标签"
        unique_together = ('post', 'interest_tag')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.post.title} - {self.interest_tag.name}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'tag_id': self.interest_tag.id,
            'tag_name': self.interest_tag.name,
            'tag_color': self.interest_tag.color,
            'tag_category': self.interest_tag.category
        }


# 违规词库模型
class ViolationWord(models.Model):
    MATCH_TYPE_CHOICES = [
        ('exact', '精确匹配'),
        ('contains', '包含匹配'), 
        ('regex', '正则表达式'),
        ('fuzzy', '模糊匹配')
    ]
    
    CATEGORY_CHOICES = [
        ('political', '政治敏感'),
        ('adult', '色情内容'),
        ('violence', '暴力血腥'),
        ('advertisement', '垃圾广告'),
        ('abuse', '恶意谩骂'),
        ('other', '其他违规')
    ]
    
    word = models.CharField(max_length=200, verbose_name='违规词/模式')
    pattern = models.TextField(blank=True, verbose_name='正则表达式')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='违规类别')
    severity = models.IntegerField(default=2, verbose_name='严重程度', 
                                 help_text='1-警告，2-拒绝，3-严重违规')
    match_type = models.CharField(max_length=10, choices=MATCH_TYPE_CHOICES, 
                                default='contains', verbose_name='匹配方式')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '违规词库'
        verbose_name_plural = '违规词库'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.word} ({self.get_category_display()})"
    
    def to_dict(self):
        return {
            'id': self.id,
            'word': self.word,
            'pattern': self.pattern,
            'category': self.category,
            'category_display': self.get_category_display(),
            'severity': self.severity,
            'match_type': self.match_type,
            'match_type_display': self.get_match_type_display(),
            'is_active': self.is_active
        }


# 内容审核日志模型
class ModerationLog(models.Model):
    ACTION_CHOICES = [
        ('approved', '通过'),
        ('blocked', '拒绝'),
        ('warning', '警告')
    ]
    
    CONTENT_TYPE_CHOICES = [
        ('title', '标题'),
        ('content', '正文'),
        ('both', '标题和正文')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, 
                                  verbose_name='内容类型')
    original_content = models.TextField(verbose_name='原始内容')
    detected_words = models.TextField(default='[]', verbose_name='检测到的违规词',
                                    help_text='JSON格式存储')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='处理动作')
    violation_category = models.CharField(max_length=20, blank=True, verbose_name='违规类别')
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, blank=True, 
                           verbose_name='关联帖子')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='检测时间')
    
    class Meta:
        verbose_name = '内容审核日志'
        verbose_name_plural = '内容审核日志'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.created_at}"
    
    def get_detected_words_list(self):
        """获取检测到的违规词列表"""
        try:
            return json.loads(self.detected_words)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_detected_words_list(self, words_list):
        """设置检测到的违规词列表"""
        self.detected_words = json.dumps(words_list, ensure_ascii=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'username': self.user.username,
            'content_type': self.content_type,
            'content_type_display': self.get_content_type_display(),
            'original_content': self.original_content[:100] + '...' if len(self.original_content) > 100 else self.original_content,
            'detected_words': self.get_detected_words_list(),
            'action': self.action,
            'action_display': self.get_action_display(),
            'violation_category': self.violation_category,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

# 帖子点赞模型
class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes', verbose_name='帖子')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes', verbose_name='用户')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='点赞时间')
    
    class Meta:
        verbose_name = '帖子点赞'
        verbose_name_plural = '帖子点赞'
        unique_together = ('post', 'user')  # 防止重复点赞
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} 赞了 {self.post.title}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'username': self.user.username,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


# 帖子评论模型
class PostComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='帖子')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments', verbose_name='用户')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='replies', verbose_name='父评论')
    content = models.TextField(verbose_name='评论内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评论时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')
    
    class Meta:
        verbose_name = '帖子评论'
        verbose_name_plural = '帖子评论'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} 评论了 {self.post.title}"
    
    def to_dict(self, include_replies=True):
        data = {
            'id': self.id,
            'user_id': self.user.id,
            'username': self.user.username,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_author': False,  # 这个字段会在视图中根据当前用户设置
            'parent_id': self.parent.id if self.parent else None,
            'replies_count': self.replies.filter(is_deleted=False).count()
        }
        
        # 如果包含回复且不是删除的评论，则加载回复
        if include_replies and not self.is_deleted:
            data['replies'] = [reply.to_dict(include_replies=False) for reply in 
                              self.replies.filter(is_deleted=False)[:5]]  # 最多显示5条回复
        
        return data
