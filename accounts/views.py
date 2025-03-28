from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import User
from .decorators import login_required
from django.template.loader import render_to_string
import os
from django.conf import settings

# Create your views here.
@csrf_exempt
def register(request):
    """用户注册视图"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            phone = data.get('phone')
            
            if not all([username, password, email]):
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名、密码和邮箱不能为空'
                }, status=400)
            
            user, message = User.register(username, password, email, phone)
            
            if user:
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'data': {
                        'username': user.username,
                        'email': user.email
                    }
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': message
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '无效的JSON数据'
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': '不支持的请求方法'
    }, status=405)

@csrf_exempt
def login(request):
    """用户登录视图"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')  # 可以是用户名或邮箱
            password = data.get('password')
            
            if not all([username, password]):
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名和密码不能为空'
                }, status=400)
            
            user = User.authenticate(username=username, password=password)
            
            if user:
                # 生成JWT令牌
                token = user.generate_token()
                
                return JsonResponse({
                    'status': 'success',
                    'message': '登录成功',
                    'data': {
                        'username': user.username,
                        'email': user.email,
                        'token': token  # 返回JWT令牌
                    }
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名或密码错误'
                }, status=401)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '无效的JSON数据'
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': '不支持的请求方法'
    }, status=405)

@login_required
def user_profile(request):
    """
    用户资料视图
    需要登录才能访问
    """
    # 由于使用了login_required装饰器，这里可以安全地访问request.user
    user = request.user
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'created_at': user.created_at,
            'updated_at': user.updated_at
        }
    })

@csrf_exempt
@login_required
def update_profile(request):
    """
    更新用户资料
    需要登录才能访问
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = request.user
            
            # 更新允许修改的字段
            if 'email' in data:
                user.email = data['email']
            
            if 'phone' in data:
                user.phone = data['phone']
            
            # 保存更改
            user.save()
            
            return JsonResponse({
                'status': 'success',
                'message': '资料更新成功',
                'data': {
                    'username': user.username,
                    'email': user.email,
                    'phone': user.phone
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '无效的JSON数据'
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': '不支持的请求方法'
    }, status=405)

# 前端页面渲染
def home_page(request):
    """首页"""
    # 直接读取HTML文件并返回，完全跳过Django模板系统
    home_html_path = os.path.join(settings.BASE_DIR, 'htmls', 'accounts', 'home.html')
    
    with open(home_html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HttpResponse(html_content)

def auth_page(request):
    """认证页面 - 包含登录和注册功能"""
    # 如果用户已登录，重定向到主页
    if request.user:
        return redirect('accounts:home_page')
    return render(request, 'accounts/auth.html')


