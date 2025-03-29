from django.contrib import admin
from .models import Post

# Register your models here.

# 注册Post模型到admin
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'school', 'time')
    list_filter = ('school', 'time')
    search_fields = ('title', 'content', 'author')
    date_hierarchy = 'time'
