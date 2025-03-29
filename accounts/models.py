from django.db import models
import hashlib
import re
import jwt
import datetime
from django.conf import settings
import uuid
import random
import string
from django.utils import timezone

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=50, unique=True, verbose_name="用户名")
    password = models.CharField(max_length=128, verbose_name="密码")
    email = models.EmailField(unique=True, verbose_name="邮箱")
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="手机号码")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_staff = models.BooleanField(default=False, verbose_name="是否管理员")
    is_editor = models.BooleanField(default=False, verbose_name="是否博主")
    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"
        
    def __str__(self):
        return self.username
    
    def save(self, *args, **kwargs):
        # 如果密码未加密，则进行加密
        if not self.pk or kwargs.get('update_fields') and 'password' in kwargs.get('update_fields'):
            self.password = self.encrypt_password(self.password)
        super().save(*args, **kwargs)
    
    @staticmethod
    def encrypt_password(password):
        """对密码进行加密"""
        salt = "arx_user_salt"
        hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
        return hash_obj.hexdigest()
    
    def generate_token(self):
        """生成JWT令牌"""
        # 设置过期时间为7天
        expiry = datetime.datetime.now() + datetime.timedelta(days=7)
        
        # 创建载荷
        payload = {
            'user_id': self.id,
            'username': self.username,
            'email': self.email,
            'is_staff': self.is_staff,
            'exp': expiry
        }
        
        # 生成JWT令牌
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        
        return token
    
    @classmethod
    def verify_token(cls, token):
        """验证JWT令牌"""
        try:
            # 解码令牌
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            # 获取用户ID
            user_id = payload.get('user_id')
            
            # 查询用户
            user = cls.objects.get(id=user_id)
            
            return user
        except jwt.ExpiredSignatureError:
            # 令牌已过期
            return None
        except (jwt.InvalidTokenError, cls.DoesNotExist):
            # 令牌无效或用户不存在
            return None
    
    @classmethod
    def authenticate(cls, username=None, password=None):
        """验证用户登录"""
        try:
            # 尝试通过用户名或邮箱登录
            if '@' in username:
                user = cls.objects.get(email=username)
            else:
                user = cls.objects.get(username=username)
            
            # 验证密码
            encrypted_password = cls.encrypt_password(password)
            if user.password == encrypted_password:
                return user
            return None
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def register(cls, username, password, email, phone=None):
        """注册新用户"""
        # 验证数据合法性
        if cls.objects.filter(username=username).exists():
            return None, "用户名已存在"
        
        if cls.objects.filter(email=email).exists():
            return None, "邮箱已被注册"
        
        if phone and cls.objects.filter(phone=phone).exists():
            return None, "手机号码已被注册"
            
        # 验证邮箱格式
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return None, "邮箱格式不正确"
        
        # 验证密码强度（至少8个字符，包含字母和数字）
        if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            return None, "密码必须至少8个字符，且包含字母和数字"
            
        # 验证手机号格式（如果提供）
        if phone and not re.match(r'^\d{11}$', phone):
            return None, "手机号码格式不正确"
            
        # 创建用户
        user = cls(
            username=username,
            password=password,  # 会在save方法中自动加密
            email=email,
            phone=phone
        )
        user.save()
        return user, "注册成功"

# 验证码模型
class VerificationCode(models.Model):
    email = models.EmailField(verbose_name="邮箱")
    code = models.CharField(max_length=6, verbose_name="验证码")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    is_used = models.BooleanField(default=False, verbose_name="是否已使用")
    
    class Meta:
        verbose_name = "验证码"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email}的验证码"
    
    @classmethod
    def generate_code(cls, email):
        """生成并保存验证码"""
        # 生成6位随机数字验证码
        code = ''.join(random.choices(string.digits, k=6))
        
        # 失效旧的未使用验证码
        cls.objects.filter(email=email, is_used=False).update(is_used=True)
        
        # 创建新验证码
        verification = cls.objects.create(email=email, code=code)
        return verification
    
    def is_valid(self):
        """检查验证码是否有效"""
        # 已使用的验证码无效
        if self.is_used:
            return False
        
        # 检查验证码是否过期
        now = timezone.now()
        expiry_time = self.created_at + datetime.timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
        if now > expiry_time:
            return False
        
        return True

# JWT配置
jwt_expiry_days = getattr(settings, 'JWT_EXPIRY_DAYS', 7)

# 学校模型
class School(models.Model):
    name = models.CharField(max_length=100, verbose_name='学校名称')
    address = models.CharField(max_length=200, verbose_name='地址', blank=True, null=True)
    description = models.TextField(verbose_name='描述', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '学校'
        verbose_name_plural = '学校'
        ordering = ['id']

    def __str__(self):
        return self.name
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'description': self.description
        }
