from .models import User

class JWTAuthMiddleware:
    """
    JWT认证中间件
    从请求头中获取JWT令牌，验证并解析用户信息
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # 从请求头中获取JWT令牌
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        # 初始化请求对象的用户属性
        request.user = None
        request.auth = None
        
        # 如果存在认证头且以Bearer开头
        if auth_header.startswith('Bearer '):
            # 提取令牌
            token = auth_header.split(' ')[1]
            
            # 验证令牌
            user = User.verify_token(token)
            
            if user:
                # 将用户信息添加到请求对象
                request.user = user
                request.auth = token
        
        # 继续处理请求
        response = self.get_response(request)
        return response 