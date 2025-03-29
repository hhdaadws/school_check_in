from django.contrib import admin
from .models import ChatMessage
# Register your models here.
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'content', 'timestamp')  # 将 timestamp 和其他需要显示的字段加入
    list_filter = ('timestamp',)  # 可选：添加日期过滤器
    search_fields = ('content',)  # 可选：添加搜索功能

admin.site.register(ChatMessage, ChatMessageAdmin)  # 注册时传入自定义的 ModelAdmin