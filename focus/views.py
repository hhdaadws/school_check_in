from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.decorators import login_required
from accounts.models import FocusSession, FocusSettings, User
import json
from django.utils import timezone
from datetime import timedelta

# Create your views here.

# 获取用户的专注设置
@login_required
def get_focus_settings(request):
    """获取用户的专注设置"""
    try:
        settings, created = FocusSettings.objects.get_or_create(
            user=request.user,
            defaults={
                'work_duration': 25,
                'break_duration': 5,
                'long_break_duration': 15,
                'sessions_before_long_break': 4,
                'sound_enabled': True,
                'auto_start_breaks': False,
                'auto_start_work': False,
                'focus_theme': 'default'
            }
        )
        return JsonResponse({
            'success': True,
            'settings': settings.to_dict()
        })
    except Exception as e:
        return JsonResponse({'error': f'获取设置失败: {str(e)}'}, status=500)

# 更新用户的专注设置
@csrf_exempt
@login_required
def update_focus_settings(request):
    """更新用户的专注设置"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    
    try:
        data = json.loads(request.body)
        settings, created = FocusSettings.objects.get_or_create(user=request.user)
        
        # 更新设置
        if 'work_duration' in data:
            settings.work_duration = data['work_duration']
        if 'break_duration' in data:
            settings.break_duration = data['break_duration']
        if 'long_break_duration' in data:
            settings.long_break_duration = data['long_break_duration']
        if 'sessions_before_long_break' in data:
            settings.sessions_before_long_break = data['sessions_before_long_break']
        if 'sound_enabled' in data:
            settings.sound_enabled = data['sound_enabled']
        if 'auto_start_breaks' in data:
            settings.auto_start_breaks = data['auto_start_breaks']
        if 'auto_start_work' in data:
            settings.auto_start_work = data['auto_start_work']
        if 'focus_theme' in data:
            settings.focus_theme = data['focus_theme']
        
        settings.save()
        
        return JsonResponse({
            'success': True,
            'message': '设置更新成功',
            'settings': settings.to_dict()
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'更新设置失败: {str(e)}'}, status=500)

# 开始专注会话
@csrf_exempt
@login_required
def start_focus_session(request):
    """开始一个新的专注会话"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    
    try:
        data = json.loads(request.body)
        task_title = data.get('task_title', '专注任务')
        task_description = data.get('task_description', '')
        planned_duration = data.get('planned_duration', 25)
        session_type = data.get('session_type', 'work')
        
        # 检查是否有正在进行的会话
        active_session = FocusSession.objects.filter(
            user=request.user,
            end_time__isnull=True
        ).first()
        
        if active_session:
            return JsonResponse({
                'error': '已有正在进行的专注会话',
                'active_session': active_session.to_dict()
            }, status=400)
        
        # 创建新的专注会话
        session = FocusSession.objects.create(
            user=request.user,
            task_title=task_title,
            task_description=task_description,
            planned_duration=planned_duration,
            session_type=session_type
        )
        
        return JsonResponse({
            'success': True,
            'message': '专注会话已开始',
            'session': session.to_dict()
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'开始会话失败: {str(e)}'}, status=500)

# 结束专注会话
@csrf_exempt
@login_required
def end_focus_session(request):
    """结束当前的专注会话"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        completed = data.get('completed', False)
        interrupted = data.get('interrupted', False)
        
        if not session_id:
            return JsonResponse({'error': '会话ID不能为空'}, status=400)
        
        session = FocusSession.objects.get(
            id=session_id,
            user=request.user,
            end_time__isnull=True
        )
        
        # 计算实际时长
        now = timezone.now()
        actual_duration = int((now - session.start_time).total_seconds() / 60)
        
        session.end_time = now
        session.actual_duration = actual_duration
        session.completed = completed
        session.interrupted = interrupted
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': '专注会话已结束',
            'session': session.to_dict()
        })
    except FocusSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在或已结束'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'结束会话失败: {str(e)}'}, status=500)

# 获取当前活动的会话
@login_required
def get_active_session(request):
    """获取当前用户的活动会话"""
    try:
        session = FocusSession.objects.filter(
            user=request.user,
            end_time__isnull=True
        ).first()
        
        if session:
            return JsonResponse({
                'success': True,
                'session': session.to_dict()
            })
        else:
            return JsonResponse({
                'success': True,
                'session': None
            })
    except Exception as e:
        return JsonResponse({'error': f'获取会话失败: {str(e)}'}, status=500)

# 获取专注会话历史
@login_required
def get_focus_history(request):
    """获取用户的专注会话历史"""
    try:
        # 获取查询参数
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        sessions = FocusSession.objects.filter(
            user=request.user
        ).order_by('-start_time')[offset:offset+limit]
        
        data = [session.to_dict() for session in sessions]
        
        return JsonResponse({
            'success': True,
            'sessions': data,
            'count': FocusSession.objects.filter(user=request.user).count()
        })
    except Exception as e:
        return JsonResponse({'error': f'获取历史失败: {str(e)}'}, status=500)

# 获取专注统计数据
@login_required
def get_focus_stats(request):
    """获取用户的专注统计数据"""
    try:
        now = timezone.now()
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # 今日统计
        today_sessions = FocusSession.objects.filter(
            user=request.user,
            start_time__date=today,
            session_type='work'
        )
        
        # 本周统计
        week_sessions = FocusSession.objects.filter(
            user=request.user,
            start_time__date__gte=week_start,
            session_type='work'
        )
        
        # 本月统计
        month_sessions = FocusSession.objects.filter(
            user=request.user,
            start_time__date__gte=month_start,
            session_type='work'
        )
        
        # 计算统计数据
        stats = {
            'today': {
                'sessions_count': today_sessions.count(),
                'completed_sessions': today_sessions.filter(completed=True).count(),
                'total_minutes': sum(s.actual_duration or 0 for s in today_sessions),
            },
            'week': {
                'sessions_count': week_sessions.count(),
                'completed_sessions': week_sessions.filter(completed=True).count(),
                'total_minutes': sum(s.actual_duration or 0 for s in week_sessions),
            },
            'month': {
                'sessions_count': month_sessions.count(),
                'completed_sessions': month_sessions.filter(completed=True).count(),
                'total_minutes': sum(s.actual_duration or 0 for s in month_sessions),
            },
            'total': {
                'sessions_count': FocusSession.objects.filter(user=request.user, session_type='work').count(),
                'completed_sessions': FocusSession.objects.filter(user=request.user, session_type='work', completed=True).count(),
                'total_minutes': sum(s.actual_duration or 0 for s in FocusSession.objects.filter(user=request.user, session_type='work')),
            }
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({'error': f'获取统计失败: {str(e)}'}, status=500)
