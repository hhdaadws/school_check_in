from django.contrib import admin
from .models import Checkin, UserCheckin

# Register your models here.
@admin.register(Checkin)
class CheckinAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'time', 'created_at']
    list_filter = ['user']
    search_fields = ['title', 'description']
    
@admin.register(UserCheckin)
class UserCheckinAdmin(admin.ModelAdmin):
    list_display = ['user', 'checkin_id', 'checkin_title', 'checked_at', 'checkin_date']
    list_filter = ['user', 'checkin_id']
    search_fields = ['user__username', 'checkin__title', 'checkin_title']
