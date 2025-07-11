from .models import User
import logging

# 设置日志记录器
logger = logging.getLogger(__name__)

class JWTAuthMiddleware:
    """
    JWT认证中间件
    从请求头中获取JWT令牌，验证并解析用户信息
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # 跳过Django admin路径的认证中间件
        if request.path.startswith('/admin/'):
            logger.debug(f"Skipping JWT auth for Django admin path: {request.path}")
            return self.get_response(request)
            
        logger.debug(f"JWT middleware processing: {request.path}")
            
        # 从请求头中获取JWT令牌
        auth_header = request.headers.get('Authorization')
        
        # 尝试从Cookie中获取token
        auth_cookie = request.COOKIES.get('token')
        
        # 从localStorage获取token (通过前端代码设置的请求头)
        auth_ls = request.headers.get('X-Auth-Token')
        
        # 初始化请求对象的用户属性
        request.user = None
        request.auth = None
        
        token = None
        token_source = None
        
        # 按优先级尝试获取token
        if auth_header and auth_header.startswith('Bearer '):
            # 提取令牌
            token = auth_header.split(' ')[1]
            token_source = 'Authorization header'
        elif auth_ls:
            token = auth_ls
            token_source = 'X-Auth-Token header'
        elif auth_cookie:
            token = auth_cookie
            token_source = 'Cookie'
            
        if token:
            try:
                # 验证令牌
                user = User.verify_token(token)
                
                if user:
                    # 将用户信息添加到请求对象
                    request.user = user
                    request.auth = token
                    logger.debug(f"User authenticated: {user.username} via {token_source}")
                else:
                    logger.warning(f"Token verification failed for token from {token_source}")
                    # 确保user为None
                    request.user = None
                    request.auth = None
            except Exception as e:
                logger.error(f"Token verification error: {str(e)} (token from {token_source})")
                # 确保在异常情况下user为None
                request.user = None
                request.auth = None
        else:
            logger.debug(f"No token found for path: {request.path}")
            # 确保在没有token的情况下user为None
            request.user = None
            request.auth = None
        
        # 确保request.user始终有一个明确的值
        if not hasattr(request, 'user') or request.user is None:
            request.user = None
            logger.debug("Set request.user to None (no user found)")
        
        # 如果是直接访问管理员页面并有特殊参数，确保设置cookie
        if request.path == '/accounts/admin/' and request.GET.get('direct_access') == 'true' and auth_header:
            response = self.get_response(request)
            # 确保在响应中设置cookie，以供后续请求使用
            if not auth_cookie and auth_header:
                token = auth_header.replace('Bearer ', '')
                response.set_cookie('token', token, max_age=86400)
            return response
            
        # 继续处理请求
        response = self.get_response(request)
        return response 