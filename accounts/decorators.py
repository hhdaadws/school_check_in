from functools import wraps
from django.http import JsonResponse

def login_required(view_func):
    """
    用户认证装饰器
    用于保护需要登录才能访问的视图
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 检查请求对象是否包含用户信息
        if not request.user:
            return JsonResponse({
                'status': 'error',
                'message': '请先登录'
            }, status=401)
        
        # 调用原始视图函数
        return view_func(request, *args, **kwargs)
    
    return wrapper 