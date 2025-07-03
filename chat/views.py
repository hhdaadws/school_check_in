from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.models import School
from accounts.decorators import login_required
import os
from django.conf import settings
from .models import ChatMessage
from accounts.models import User
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.utils import timezone

# Create your views here.

@login_required
def chat_room(request, school_id):
    """
    渲染聊天室页面
    直接返回静态HTML页面，不使用Django模板
    """
    # 直接读取HTML文件并返回，完全跳过Django模板系统
    chat_room_path = os.path.join(settings.BASE_DIR, 'htmls', 'chat', 'chat_room.html')
    
    with open(chat_room_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HttpResponse(html_content)

@login_required
def chat_room_data(request, school_id):
    """
    提供聊天室数据的API
    返回JSON格式的学校信息和聊天室名称
    """
    try:
        school = School.objects.get(id=school_id)
        data = {
            'school': {
                'id': school.id,
                'name': school.name
            },
            'room_name': f'school_{school_id}'  # 聊天室名称用学校ID标识
        }
        return JsonResponse(data)
    except School.DoesNotExist:
        return JsonResponse({'error': '学校不存在'}, status=404)

@login_required
def chat_rooms(request):
    """
    获取所有可用的聊天室列表
    """
    schools = School.objects.all()
    data = [{
        'id': school.id,
        'name': school.name,
        'room_name': f'school_{school.id}'
    } for school in schools]
    return JsonResponse(data, safe=False)

class ChatMessageEncoder(DjangoJSONEncoder):
    """自定义JSON编码器，处理ChatMessage对象"""
    def default(self, obj):
        if isinstance(obj, ChatMessage):
            return {
                'id': obj.id,
                'sender': obj.sender.username,
                'content': obj.content,
                'timestamp': obj.timestamp.isoformat()
            }
        return super().default(obj)

@login_required
def chat_history(request, room_name):
    """
    获取聊天室的历史记录
    默认返回最近100条消息
    支持分页和指定消息数量
    """
    try:
        # 获取请求参数
        limit = int(request.GET.get('limit', 100))  # 默认获取100条
        offset = int(request.GET.get('offset', 0))  # 默认从最新消息开始
        
        # 限制最大获取数量，防止请求过大
        if limit > 100:
            limit = 100
            
        # 查询指定房间的历史消息
        messages = ChatMessage.objects.filter(
            room_name=room_name
        ).order_by('-timestamp')[offset:offset+limit]
        
        # 将查询结果转换为列表并反转，使最早的消息在前
        message_list = list(reversed(messages))
        
        # 使用自定义编码器序列化消息
        data = json.dumps(message_list, cls=ChatMessageEncoder)
        
        return HttpResponse(data, content_type='application/json')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def clear_chat_messages(request, room_name):
    """
    清除聊天室消息
    支持两种模式：
    1. 管理员可以清空整个聊天室
    2. 普通用户可以删除自己的消息
    """
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    
    try:
        # 获取请求参数
        data = json.loads(request.body)
        clear_type = data.get('type', 'own')  # 'all' 或 'own'
        
        # 检查用户权限
        is_admin = getattr(request.user, 'is_staff', False)
        
        if clear_type == 'all':
            # 清空整个聊天室（仅管理员）
            if not is_admin:
                return JsonResponse({'error': '权限不足，只有管理员可以清空聊天室'}, status=403)
            
            # 删除指定聊天室的所有消息
            deleted_count = ChatMessage.objects.filter(room_name=room_name).count()
            ChatMessage.objects.filter(room_name=room_name).delete()
            
            return JsonResponse({
                'success': True,
                'message': f'已清空聊天室，删除了 {deleted_count} 条消息',
                'deleted_count': deleted_count,
                'type': 'all'
            })
            
        elif clear_type == 'own':
            # 删除用户自己的消息
            deleted_count = ChatMessage.objects.filter(
                room_name=room_name,
                sender=request.user
            ).count()
            
            ChatMessage.objects.filter(
                room_name=room_name,
                sender=request.user
            ).delete()
            
            return JsonResponse({
                'success': True,
                'message': f'已删除您的 {deleted_count} 条消息',
                'deleted_count': deleted_count,
                'type': 'own'
            })
        else:
            return JsonResponse({'error': '无效的清除类型'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'清除失败: {str(e)}'}, status=500)

@login_required
@csrf_exempt
def send_message(request, room_name):
    """
    发送聊天消息到数据库
    """
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    
    try:
        # 获取请求参数
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'error': '消息内容不能为空'}, status=400)
        
        # 创建消息记录
        message = ChatMessage.objects.create(
            room_name=room_name,
            sender=request.user,
            content=content,
            timestamp=timezone.now()
        )
        
        # 返回保存的消息数据
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'sender': message.sender.username,
                'timestamp': message.timestamp.isoformat(),
                'isOwn': True
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'发送消息失败: {str(e)}'}, status=500)
