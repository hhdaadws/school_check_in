from functools import wraps
from django.http import JsonResponse
import jwt
from django.conf import settings
from .models import User

def login_required(view_func):
    """
    用户认证装饰器
    用于保护需要登录才能访问的视图
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 检查用户是否已登录
        if not hasattr(request, 'user') or not request.user or request.user.id is None:
            return JsonResponse({'error': '请先登录'}, status=401)
        return view_func(request, *args, **kwargs)
    
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # 检查用户是否已登录
        if not hasattr(request, 'user') or not request.user or request.user.id is None:
            return JsonResponse({'error': '请先登录'}, status=401)
        
        # 检查用户是否是管理员
        if not request.user.is_staff:
            return JsonResponse({'error': '权限不足，需要管理员权限'}, status=403)
            
        return view_func(request, *args, **kwargs)
    return wrapped_view 