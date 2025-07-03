from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from .models import User, VerificationCode, School, InterestTag, UserInterest
from .decorators import admin_required, login_required
from django.template.loader import render_to_string
import os
from django.conf import settings
from django.core.mail import send_mail
import random
import string
from django.utils import timezone
from django.views.decorators.http import require_POST

# Cloudflare Turnstile配置
TURNSTILE_SECRET_KEY = '0x4AAAAAABC3iatF16AlFFAM3lV-rxs58Mo'  # 替换为你的密钥
TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

# 验证Cloudflare Turnstile令牌
def verify_turnstile(token, remote_ip=None):
    #  开发环境中自动通过验证
    if getattr(settings, 'DEV_ENVIRONMENT', False):
        print("[开发环境] 人机验证自动通过")
        return True
    
    data = {
        'secret': settings.TURNSTILE_SECRET_KEY,
        'response': token
    }
    
    if remote_ip:
        data['remoteip'] = remote_ip
    
    try:
        response = requests.post(settings.TURNSTILE_VERIFY_URL, data=data)
        result = response.json()
        success = result.get('success', False)
        
        if not success:
            error_codes = result.get('error-codes', [])
            print(f"Turnstile验证失败，错误代码: {error_codes}")
        
        return success
    except Exception as e:
        print(f"Turnstile验证异常: {str(e)}")
        return False

# Create your views here.
@csrf_exempt
def send_verification_code(request):
    """发送验证码到用户邮箱"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({"error": "邮箱不能为空"}, status=400)
        
        # 生成验证码
        code = ''.join(random.choices(string.digits, k=6))
        
        # 保存验证码到数据库
        VerificationCode.objects.create(
            email=email,
            code=code,
            created_at=timezone.now()
        )
        
        # 发送验证码邮件
        subject = '【Arx学习平台】邮箱验证码'
        message = f'您的验证码是: {code}, 有效期10分钟。如非本人操作，请忽略此邮件。'
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [email]
        
        try:
            send_mail(subject, message, from_email, recipient_list)
            return JsonResponse({
                "success": True,
                "message": "验证码已发送，请查收邮件"
            })
        except Exception as e:
            return JsonResponse({"error": f"发送邮件失败: {str(e)}"}, status=500)
            
    except Exception as e:
        return JsonResponse({"error": f"发送验证码失败: {str(e)}"}, status=500)

@csrf_exempt
def register(request):
    """用户注册"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            phone = data.get('phone', '')
            verification_code = data.get('verification_code')
            captcha_token = data.get('captcha_token')
            
            # 验证必要字段
            if not all([username, password, email, verification_code, captcha_token]):
                return JsonResponse({'status': 'error', 'message': '请填写所有必要字段'})
            
            # 验证Cloudflare Turnstile
            if not verify_turnstile(captcha_token, request.META.get('REMOTE_ADDR')):
                return JsonResponse({'status': 'error', 'message': '人机验证失败，请重试'})
            
            # 验证邮箱验证码
            try:
                latest_code = VerificationCode.objects.filter(
                    email=email, 
                    is_used=False
                ).latest('created_at')
                
                if not latest_code or not latest_code.is_valid():
                    return JsonResponse({'status': 'error', 'message': '验证码已过期'})
                
                if latest_code.code != verification_code:
                    return JsonResponse({'status': 'error', 'message': '验证码错误'})
                
                # 标记验证码为已使用
                latest_code.is_used = True
                latest_code.save()
                
            except VerificationCode.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': '请先获取验证码'})
            
            # 创建用户
            user, message = User.register(username, password, email, phone)
            
            if user:
                # 生成JWT令牌
                token = user.generate_token()
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'username': user.username,
                    'email': user.email,
                    'token': token
                })
            else:
                return JsonResponse({'status': 'error', 'message': message})
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': '无效的请求数据'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'注册失败: {str(e)}'})
    else:
        return JsonResponse({'status': 'error', 'message': '不支持的请求方法'})

@csrf_exempt
def login(request):
    """用户登录视图"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')  # 可以是用户名或邮箱
            password = data.get('password')
            captcha_token = data.get('captcha_token')
            
            if not all([username, password, captcha_token]):
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名、密码和验证码不能为空'
                }, status=400)
            
            # 验证Cloudflare Turnstile
            if not verify_turnstile(captcha_token, request.META.get('REMOTE_ADDR')):
                return JsonResponse({'status': 'error', 'message': '人机验证失败，请重试'}, status=400)
            
            user = User.authenticate(username=username, password=password)
            
            if user:
                # 生成JWT令牌
                token = user.generate_token()
                
                return JsonResponse({
                    'status': 'success', 
                    'message': '登录成功', 
                    'username': user.username,
                    'email': user.email,
                    'token': token,  # 返回JWT令牌
                    'is_staff': user.is_staff,  # 添加是否管理员标志
                    'user_id': user.id,  # 添加用户ID
                    'interests_selected': user.interests_selected  # 添加兴趣标签选择状态
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
            'is_staff': user.is_staff,
            'is_editor': user.is_editor
        }
    })


@csrf_exempt

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
    home_html_path = os.path.join(settings.BASE_DIR, 'htmls','accounts','home.html')
    
    with open(home_html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HttpResponse(html_content)

def auth_page(request):
    """认证页面"""
    # 如果用户已登录，重定向到首页
    token = request.COOKIES.get('token')
    if token:
        return redirect('accounts:home_page')
    
    # 获取要显示的标签页
    active_tab = request.GET.get('tab', 'login')
    
    # 渲染认证页面
    context = {
        'active_tab': active_tab,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'dev_environment': settings.DEV_ENVIRONMENT
    }
    return render(request, 'accounts/auth.html', context)

# 更新邮箱
@csrf_exempt

@require_POST
def update_email(request):
    """更新用户邮箱"""
    try:
        data = json.loads(request.body)
        old_email = data.get('old_email')
        old_code = data.get('old_code')
        new_email = data.get('new_email')
        new_code = data.get('new_code')
        
        # 验证参数
        if not all([old_email, old_code, new_email, new_code]):
            return JsonResponse({"error": "所有字段都必须填写"}, status=400)
            
        # 验证原邮箱是否正确
        if old_email != request.user.email:
            return JsonResponse({"error": "原邮箱不正确"}, status=400)
            
        # 检查新邮箱是否已被使用
        if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
            return JsonResponse({"error": "该邮箱已被其他用户使用"}, status=400)
            
        # 验证原邮箱验证码
        old_verification = VerificationCode.objects.filter(
            email=old_email,
            code=old_code,
            is_used=False
        ).order_by('-created_at').first()
        
        if not old_verification:
            return JsonResponse({"error": "原邮箱验证码无效或已过期"}, status=400)
            
        # 验证新邮箱验证码
        new_verification = VerificationCode.objects.filter(
            email=new_email,
            code=new_code,
            is_used=False
        ).order_by('-created_at').first()
        
        if not new_verification:
            return JsonResponse({"error": "新邮箱验证码无效或已过期"}, status=400)
            
        # 检查验证码是否过期
        now = timezone.now()
        expiry_minutes = getattr(settings, 'VERIFICATION_CODE_EXPIRE_MINUTES', 10)
        
        if (now - old_verification.created_at).total_seconds() > expiry_minutes * 60:
            return JsonResponse({"error": "原邮箱验证码已过期"}, status=400)
            
        if (now - new_verification.created_at).total_seconds() > expiry_minutes * 60:
            return JsonResponse({"error": "新邮箱验证码已过期"}, status=400)
            
        # 更新用户邮箱
        request.user.email = new_email
        request.user.save(update_fields=['email'])
        
        # 标记验证码为已使用
        old_verification.is_used = True
        old_verification.save()
        new_verification.is_used = True
        new_verification.save()
        
        # 将更新后的用户信息返回
        user_data = {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'phone': request.user.phone,
            'date_joined': request.user.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return JsonResponse({
            "success": True,
            "message": "邮箱更新成功",
            "user": user_data
        })
        
    except Exception as e:
        return JsonResponse({"error": f"更新邮箱失败: {str(e)}"}, status=500)

# =============== 兴趣标签相关视图 ===============

@csrf_exempt
def get_interest_tags(request):
    """获取所有可用的兴趣标签"""
    try:
        tags = InterestTag.objects.filter(is_active=True).order_by('category', 'name')
        
        # 按分类分组
        categories = {}
        for tag in tags:
            if tag.category not in categories:
                categories[tag.category] = []
            categories[tag.category].append(tag.to_dict())
        
        return JsonResponse({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        return JsonResponse({'error': f'获取兴趣标签失败: {str(e)}'}, status=500)

@csrf_exempt
def select_interests(request):
    """用户选择兴趣标签"""
    from .decorators import login_required
    
    # 手动检查用户登录状态
    if not hasattr(request, 'user') or not request.user or request.user.id is None:
        return JsonResponse({'error': '请先登录'}, status=401)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            interest_ids = data.get('interest_ids', [])
            
            if len(interest_ids) < 3:
                return JsonResponse({'error': '至少选择3个兴趣标签'}, status=400)
            
            if len(interest_ids) > 10:
                return JsonResponse({'error': '最多选择10个兴趣标签'}, status=400)
            
            # 验证标签ID是否有效
            valid_tags = InterestTag.objects.filter(id__in=interest_ids, is_active=True)
            if len(valid_tags) != len(interest_ids):
                return JsonResponse({'error': '包含无效的兴趣标签'}, status=400)
            
            # 清除现有选择
            UserInterest.objects.filter(user=request.user).delete()
            
            # 添加新选择
            user_interests = []
            for interest_id in interest_ids:
                user_interests.append(UserInterest(
                    user=request.user,
                    interest_tag_id=interest_id
                ))
            
            UserInterest.objects.bulk_create(user_interests)
            
            # 更新用户状态
            request.user.interests_selected = True
            request.user.interests_selected_at = timezone.now()
            request.user.save(update_fields=['interests_selected', 'interests_selected_at'])
            
            return JsonResponse({
                'success': True,
                'message': '兴趣标签选择成功'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': '无效的JSON数据'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'选择兴趣标签失败: {str(e)}'}, status=500)
    
    return JsonResponse({'error': '不支持的请求方法'}, status=405)

@csrf_exempt
def get_user_interests(request):
    """获取用户的兴趣标签"""
    # 手动检查用户登录状态
    if not hasattr(request, 'user') or not request.user or request.user.id is None:
        return JsonResponse({'error': '请先登录'}, status=401)
    
    try:
        user_interests = UserInterest.objects.filter(user=request.user).select_related('interest_tag')
        interests = []
        for ui in user_interests:
            interests.append(ui.interest_tag.to_dict())
        
        return JsonResponse({
            'success': True,
            'interests': interests,
            'interests_selected': request.user.interests_selected,
            'interests_selected_at': request.user.interests_selected_at.isoformat() if request.user.interests_selected_at else None
        })
    except Exception as e:
        return JsonResponse({'error': f'获取用户兴趣失败: {str(e)}'}, status=500)

def interests_page(request):
    """兴趣标签选择页面"""
    # 如果用户未登录，重定向到登录页面
    if not hasattr(request, 'user') or not request.user or request.user.id is None:
        return redirect('accounts:auth_page')
    
    # 如果用户已经选择过兴趣标签，重定向到首页
    if request.user.interests_selected:
        return redirect('accounts:home_page')
    
    # 读取兴趣选择页面的HTML文件
    interests_html_path = os.path.join(settings.BASE_DIR, 'htmls', 'accounts', 'interests.html')
    
    try:
        with open(interests_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HttpResponse(html_content)
    except FileNotFoundError:
        # 如果HTML文件不存在，返回简单的错误页面
        return HttpResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>兴趣标签选择</title></head>
        <body>
            <h1>兴趣标签选择页面</h1>
            <p>页面正在建设中...</p>
            <a href="/accounts/">返回首页</a>
        </body>
        </html>
        """)

@csrf_exempt  
def skip_interests(request):
    """跳过兴趣标签选择"""
    # 手动检查用户登录状态
    if not hasattr(request, 'user') or not request.user or request.user.id is None:
        return JsonResponse({'error': '请先登录'}, status=401)
    
    if request.method == 'POST':
        try:
            # 更新用户状态为已选择兴趣（即使跳过了）
            request.user.interests_selected = True
            request.user.interests_selected_at = timezone.now()
            request.user.save(update_fields=['interests_selected', 'interests_selected_at'])
            
            return JsonResponse({
                'success': True,
                'message': '已跳过兴趣标签选择'
            })
        except Exception as e:
            return JsonResponse({'error': f'跳过兴趣标签选择失败: {str(e)}'}, status=500)
    
    return JsonResponse({'error': '不支持的请求方法'}, status=405)