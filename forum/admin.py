from django.contrib import admin
from django.utils import timezone
from .models import Post, ViolationWord, ModerationLog, PostLike, PostComment

# Register your models here.

# 注册Post模型到admin
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'school', 'status', 'auto_approved', 'time')
    list_filter = ('status', 'auto_approved', 'school', 'time')
    search_fields = ('title', 'content', 'author')
    readonly_fields = ['time', 'auto_approved', 'moderation_result']
    date_hierarchy = 'time'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'author', 'content', 'school', 'user')
        }),
        ('审核信息', {
            'fields': ('status', 'reviewed_by', 'reviewed_time', 'reject_reason', 'auto_approved', 'moderation_result')
        }),
        ('时间信息', {
            'fields': ('time',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if obj.status == 'approved' and not obj.reviewed_by and not obj.auto_approved:
            obj.reviewed_by = request.user
            obj.reviewed_time = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ViolationWord)
class ViolationWordAdmin(admin.ModelAdmin):
    list_display = ['word', 'category', 'severity', 'match_type', 'is_active', 'created_at']
    list_filter = ['category', 'severity', 'match_type', 'is_active', 'created_at']
    search_fields = ['word', 'pattern']
    list_editable = ['is_active', 'severity']
    
    fieldsets = (
        ('违规词信息', {
            'fields': ('word', 'pattern', 'category', 'severity', 'match_type')
        }),
        ('状态设置', {
            'fields': ('is_active',)
        })
    )
    
    actions = ['enable_words', 'disable_words', 'test_detection']
    
    def enable_words(self, request, queryset):
        """批量启用违规词"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'已启用 {updated} 个违规词')
        # 刷新缓存
        from .moderation import TextModerationService
        TextModerationService.refresh_cache()
    enable_words.short_description = "启用选中的违规词"
    
    def disable_words(self, request, queryset):
        """批量禁用违规词"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'已禁用 {updated} 个违规词')
        # 刷新缓存
        from .moderation import TextModerationService
        TextModerationService.refresh_cache()
    disable_words.short_description = "禁用选中的违规词"
    
    def test_detection(self, request, queryset):
        """测试违规词检测功能"""
        test_text = "这是一个包含测试政治词和广告的测试文本"
        from .moderation import moderation_service
        
        is_valid, violations = moderation_service.check_text(test_text)
        result = "通过" if is_valid else f"检测到违规: {violations}"
        
        self.message_user(request, f'测试结果: {result}')
    test_detection.short_description = "测试违规检测功能"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # 保存后刷新缓存
        from .moderation import TextModerationService
        TextModerationService.refresh_cache()


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_type', 'action', 'violation_category', 'created_at']
    list_filter = ['action', 'content_type', 'violation_category', 'created_at']
    search_fields = ['user__username', 'original_content']
    readonly_fields = ['user', 'content_type', 'original_content', 'detected_words', 
                      'action', 'violation_category', 'post', 'created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'content_type', 'action', 'violation_category')
        }),
        ('检测内容', {
            'fields': ('original_content', 'detected_words')
        }),
        ('关联信息', {
            'fields': ('post', 'created_at')
        })
    )
    
    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改日志"""
        return False


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    list_filter = ['created_at', 'post__school']
    search_fields = ['user__username', 'post__title']
    readonly_fields = ['user', 'post', 'created_at']
    
    def has_add_permission(self, request):
        """禁止手动添加点赞"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改点赞"""
        return False


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'parent', 'content_preview', 'is_deleted', 'created_at']
    list_filter = ['is_deleted', 'created_at', 'post__school']
    search_fields = ['user__username', 'post__title', 'content']
    readonly_fields = ['user', 'post', 'created_at', 'updated_at']
    list_editable = ['is_deleted']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'post', 'parent', 'content')
        }),
        ('状态信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at')
        })
    )
    
    def content_preview(self, obj):
        """显示评论内容预览"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '评论内容预览'
    
    actions = ['delete_comments', 'restore_comments']
    
    def delete_comments(self, request, queryset):
        """批量软删除评论"""
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f'已删除 {updated} 条评论')
    delete_comments.short_description = "删除选中的评论"
    
    def restore_comments(self, request, queryset):
        """批量恢复评论"""
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'已恢复 {updated} 条评论')
    restore_comments.short_description = "恢复选中的评论"
