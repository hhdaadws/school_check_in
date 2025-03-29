from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
from django.conf import settings
from accounts.decorators import admin_required
from accounts.models import User


def admin_link(request):
    """返回管理员链接页面"""
    # 直接读取HTML文件并返回，完全跳过Django模板系统
    admin_link_path = os.path.join(settings.BASE_DIR, 'htmls', 'index.html')
    
    with open(admin_link_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HttpResponse(html_content)
