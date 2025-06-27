from functools import wraps
from django.http import JsonResponse
import jwt
from django.conf import settings
from .models import User
import logging

logger = logging.getLogger(__name__)

def login_required(view_func):
    """
    用户认证装饰器
    用于保护需要登录才能访问的视图
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 详细的用户认证检查
        if not hasattr(request, 'user'):
            logger.warning(f"Request has no user attribute for path: {request.path}")
            return JsonResponse({'error': '认证信息缺失，请重新登录'}, status=401)
        
        if request.user is None:
            logger.warning(f"Request user is None for path: {request.path}")
            return JsonResponse({'error': '用户未登录，请先登录'}, status=401)
        
        if not hasattr(request.user, 'id') or request.user.id is None:
            logger.warning(f"Request user has no valid ID for path: {request.path}")
            return JsonResponse({'error': '用户信息异常，请重新登录'}, status=401)
        
        logger.debug(f"User {request.user.username} accessing {request.path}")
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