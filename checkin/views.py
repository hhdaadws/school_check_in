from django.shortcuts import render
from django.http import JsonResponse
from .models import Checkin, UserCheckin, CheckinSession
from accounts.models import School
from accounts.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, date
import json
from django.core.paginator import Paginator

# Create your views here.

# 获取打卡任务
@login_required
def get_checkins(request):
    """获取当前用户创建的或者可见的所有打卡任务，并标记打卡状态"""
    # 获取用户创建的任务
    user_created_checkins = Checkin.objects.filter(user=request.user)
    
    # 获取今天的日期
    today = timezone.now().date()
    
    # 获取用户今天已打卡的任务ID
    today_checkin_ids = UserCheckin.objects.filter(
        user=request.user,
        checkin_date=today
    ).values_list('checkin_id', flat=True)
    
    # 构建返回数据，标记用户已打卡的状态
    data = []
    for checkin in user_created_checkins:
        checkin_data = checkin.to_dict(current_user=request.user)
        # 使用模型的to_dict方法已经包含了checked_today状态和is_creator字段
        data.append(checkin_data)
            
    return JsonResponse(data, safe=False)

# 获取社区打卡任务
@login_required
def get_community_checkins(request):
    # 获取分页参数
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    
    # 获取已分享到社区的打卡记录
    community_checkins = UserCheckin.objects.filter(shared_to_community=True).order_by('-checked_at')
    
    # 创建分页器
    paginator = Paginator(community_checkins, page_size)
    
    # 获取当前页的数据
    current_page = paginator.get_page(page)
    
    # 构建返回数据
    data = []
    for checkin in current_page:
        checkin_data = checkin.to_dict()
        data.append(checkin_data)
    
    # 添加分页信息
    pagination_info = {
        'page': page,
        'page_size': page_size,
        'total': paginator.count,
        'total_pages': paginator.num_pages,
        'has_next': current_page.has_next(),
        'has_prev': current_page.has_previous(),
    }
            
    return JsonResponse({
        'checkins': data,
        'pagination': pagination_info
    })

# 创建打卡任务
@csrf_exempt
@login_required
def create_checkin(request):
    """创建新的打卡任务"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        data = json.loads(request.body)
        title = data.get('title')
        time = data.get('time', '')
        description = data.get('description', '')
        target_duration = data.get('target_duration', 0)
        
        if not title:
            return JsonResponse({"error": "任务名称不能为空"}, status=400)
        
        # 创建打卡任务
        checkin = Checkin.objects.create(
            user=request.user,
            title=title,
            time=time,
            description=description,
            target_duration=target_duration
        )
        
        return JsonResponse({
            "success": True,
            "message": "创建成功",
            "checkin": checkin.to_dict(current_user=request.user)
        })
    except Exception as e:
        return JsonResponse({"error": f"创建失败: {str(e)}"}, status=500)

# 执行打卡
@csrf_exempt
@login_required
def do_checkin(request, checkin_id):
    """执行打卡操作"""
    try:
        checkin = Checkin.objects.get(id=checkin_id)
        today = timezone.now().date()
        
        # 检查今天是否已经打卡
        if UserCheckin.objects.filter(
            user=request.user, 
            checkin_id=checkin.id,
            checkin_date=today
        ).exists():
            return JsonResponse({"error": "今天已经完成该任务"}, status=400)
        
        # 解析请求数据
        data = {}
        if request.body:
            try:
                data = json.loads(request.body)
            except:
                pass
        
        # 创建打卡记录
        user_checkin = UserCheckin.objects.create(
            user=request.user, 
            checkin_id=checkin.id,
            checkin_title=checkin.title,
            checkin_date=today,
            notes=data.get('notes', '')
        )
        
        # 如果设置了目标时长，记录开始时间并创建打卡会话
        if checkin.target_duration > 0:
            user_checkin.start_time = timezone.now()
            user_checkin.save()
            
            # 创建打卡会话
            CheckinSession.objects.create(
                user=request.user,
                checkin_id=checkin.id,
                checkin_title=checkin.title
            )
        
        return JsonResponse({
            "success": True,
            "message": "打卡成功！",
            "checkin_record": user_checkin.to_dict()
        })
    except Checkin.DoesNotExist:
        return JsonResponse({"error": "任务不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"打卡失败: {str(e)}"}, status=500)

# 更新学习时长
@csrf_exempt
@login_required
def update_study_duration(request, checkin_id):
    """更新学习类任务的学习时长"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        data = json.loads(request.body)
        today = timezone.now().date()
        
        # 获取今天的打卡记录
        user_checkin = UserCheckin.objects.get(
            user=request.user,
            checkin_id=checkin_id,
            checkin_date=today
        )
        
        # 更新时长
        if 'duration' in data:
            user_checkin.duration = data['duration']
        
        if data.get('is_end', False):
            user_checkin.end_time = timezone.now()
        
        user_checkin.save()
        
        return JsonResponse({
            "success": True,
            "message": "更新成功",
            "checkin_record": user_checkin.to_dict()
        })
    except UserCheckin.DoesNotExist:
        return JsonResponse({"error": "打卡记录不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"更新失败: {str(e)}"}, status=500)

# 暂停打卡会话
@csrf_exempt
@login_required
def pause_checkin_session(request, checkin_id):
    """暂停打卡会话"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        # 获取活跃的打卡会话
        session = CheckinSession.objects.get(
            user=request.user,
            checkin_id=checkin_id,
            is_active=True
        )
        
        if not session.is_paused:
            session.is_paused = True
            session.pause_time = timezone.now()
            session.save()
            
            return JsonResponse({
                "success": True,
                "message": f"{session.task_type}已暂停",
                "session": session.to_dict()
            })
        else:
            return JsonResponse({"error": "已经是暂停状态"}, status=400)
            
    except CheckinSession.DoesNotExist:
        return JsonResponse({"error": "打卡会话不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"暂停失败: {str(e)}"}, status=500)

# 继续打卡会话
@csrf_exempt
@login_required
def resume_checkin_session(request, checkin_id):
    """继续打卡会话"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        # 获取活跃的打卡会话
        session = CheckinSession.objects.get(
            user=request.user,
            checkin_id=checkin_id,
            is_active=True
        )
        
        if session.is_paused:
            # 计算暂停时长
            if session.pause_time:
                pause_duration = (timezone.now() - session.pause_time).total_seconds()
                session.total_paused_duration += int(pause_duration)
            
            session.is_paused = False
            session.pause_time = None
            session.save()
            
            return JsonResponse({
                "success": True,
                "message": f"继续{session.task_type}",
                "session": session.to_dict()
            })
        else:
            return JsonResponse({"error": "没有暂停"}, status=400)
            
    except CheckinSession.DoesNotExist:
        return JsonResponse({"error": "打卡会话不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"继续失败: {str(e)}"}, status=500)

# 更新打卡会话数据（现在主要用于保持会话活跃）
@csrf_exempt
@login_required
def update_checkin_session(request, checkin_id):
    """更新打卡会话数据"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        # 获取活跃的打卡会话
        session = CheckinSession.objects.get(
            user=request.user,
            checkin_id=checkin_id,
            is_active=True
        )
        
        # 更新时间戳，保持会话活跃
        session.save()
        
        return JsonResponse({
            "success": True,
            "message": "更新成功",
            "session": session.to_dict()
        })
        
    except CheckinSession.DoesNotExist:
        return JsonResponse({"error": "打卡会话不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"更新失败: {str(e)}"}, status=500)

# 结束打卡会话
@csrf_exempt
@login_required
def end_checkin_session(request, checkin_id):
    """结束打卡会话"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        today = timezone.now().date()
        
        # 获取活跃的打卡会话
        session = CheckinSession.objects.get(
            user=request.user,
            checkin_id=checkin_id,
            is_active=True
        )
        
        # 结束会话
        session.is_active = False
        session.end_time = timezone.now()
        session.save()
        
        # 更新打卡记录
        user_checkin = UserCheckin.objects.get(
            user=request.user,
            checkin_id=checkin_id,
            checkin_date=today
        )
        
        user_checkin.duration = session.get_current_duration()
        user_checkin.end_time = timezone.now()
        user_checkin.save()
        
        return JsonResponse({
            "success": True,
            "message": "任务完成",
            "checkin_record": user_checkin.to_dict()
        })
        
    except CheckinSession.DoesNotExist:
        return JsonResponse({"error": "打卡会话不存在"}, status=404)
    except UserCheckin.DoesNotExist:
        return JsonResponse({"error": "打卡记录不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"结束失败: {str(e)}"}, status=500)

# 更新运动轨迹
@csrf_exempt
@login_required
def update_sport_trajectory(request, checkin_id):
    """更新运动类任务的轨迹数据"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        data = json.loads(request.body)
        today = timezone.now().date()
        
        # 获取今天的打卡记录
        user_checkin = UserCheckin.objects.get(
            user=request.user,
            checkin_id=checkin_id,
            checkin_date=today
        )
        
        # 更新运动数据
        if 'trajectory' in data:
            user_checkin.sport_trajectory = data['trajectory']
        
        if 'distance' in data:
            user_checkin.sport_distance = data['distance']
        
        if 'duration' in data:
            user_checkin.sport_duration = data['duration']
        
        if 'end_location' in data:
            user_checkin.sport_end_location = data['end_location']
        
        user_checkin.save()
        
        # 检查是否达到目标
        checkin = Checkin.objects.get(id=checkin_id)
        is_completed = user_checkin.sport_distance >= checkin.target_distance if checkin.target_distance > 0 else True
        
        return JsonResponse({
            "success": True,
            "message": "更新成功",
            "is_completed": is_completed,
            "checkin_record": user_checkin.to_dict()
        })
    except UserCheckin.DoesNotExist:
        return JsonResponse({"error": "打卡记录不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"更新失败: {str(e)}"}, status=500)

# 删除打卡任务
@csrf_exempt
@login_required
def delete_checkin(request, checkin_id):
    """删除打卡任务"""
    if request.method != 'DELETE':
        return JsonResponse({"error": "只支持DELETE请求"}, status=405)
    
    try:
        checkin = Checkin.objects.get(id=checkin_id)
        
        # 检查是否为任务创建者
        if checkin.user.id != request.user.id:
            return JsonResponse({"error": "您没有权限删除该任务"}, status=403)
        
        # 删除任务
        checkin.delete()
        
        return JsonResponse({
            "success": True,
            "message": "任务已删除"
        })
    except Checkin.DoesNotExist:
        return JsonResponse({"error": "任务不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"删除失败: {str(e)}"}, status=500)

# 分享打卡到社区
@csrf_exempt
@login_required
def share_to_community(request, checkin_record_id):
    """分享打卡记录到社区"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        data = json.loads(request.body)
        share_notes = data.get('notes', '')
        
        # 获取打卡记录
        user_checkin = UserCheckin.objects.get(
            id=checkin_record_id,
            user=request.user
        )
        
        # 检查是否已经分享过
        if user_checkin.shared_to_community:
            return JsonResponse({"error": "该打卡记录已经分享过了"}, status=400)
        
        # 更新分享状态和备注
        user_checkin.shared_to_community = True
        if share_notes:
            user_checkin.notes = share_notes
        user_checkin.save()
        
        return JsonResponse({
            "success": True,
            "message": "分享成功！",
            "checkin_record": user_checkin.to_dict()
        })
        
    except UserCheckin.DoesNotExist:
        return JsonResponse({"error": "打卡记录不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"分享失败: {str(e)}"}, status=500)
