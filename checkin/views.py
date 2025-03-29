from django.shortcuts import render
from django.http import JsonResponse
from .models import Checkin, UserCheckin
from accounts.models import School
from accounts.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json

# Create your views here.

# 获取打卡任务
@login_required
def get_checkins(request):
    """获取当前用户创建的或者可见的所有打卡任务，并标记打卡状态"""
    # 获取用户创建的任务
    user_created_checkins = Checkin.objects.filter(user=request.user)
    
    # 获取用户已打卡的任务ID
    user_checkin_ids = UserCheckin.objects.filter(
        user=request.user
    ).values_list('checkin_id', flat=True)
    print(user_checkin_ids)
    print(user_created_checkins)
    # 构建返回数据，标记用户已打卡的状态
    data = []
    for checkin in user_created_checkins:
        checkin_data = checkin.to_dict()
        checkin_data['checked'] = checkin.id in user_checkin_ids
        checkin_data['is_creator'] = True  # 标记是否为创建者
        data.append(checkin_data)
            
    return JsonResponse(data, safe=False)

# 获取社区打卡任务
@login_required
def get_community_checkins(request):
    

    community_checkins = UserCheckin.objects.all()
    
    # 构建返回数据，标记用户已打卡的状态
    data = []
    for checkin in community_checkins:
        data.append(checkin.to_dict())
            
    return JsonResponse(data, safe=False)

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
        print(title)
        time = data.get('time', '')
        description = data.get('description', '')
        
        if not title:
            return JsonResponse({"error": "任务名称不能为空"}, status=400)
        
        # 创建打卡任务
        checkin = Checkin.objects.create(
            user=request.user,
            title=title,
            time=time,
            description=description
        )
        
        return JsonResponse({
            "success": True,
            "message": "创建成功",
            "checkin": checkin.to_dict()
        })
    except Exception as e:
        return JsonResponse({"error": f"创建失败: {str(e)}"}, status=500)

# 执行打卡
@csrf_exempt
@login_required
def do_checkin(request, checkin_id):
    """执行打卡操作"""
    # if request.method != 'POST':
    #     return JsonResponse({"error": "只支持POST请求"}, status=405)
    

    checkin = Checkin.objects.get(id=checkin_id)
        
    # 检查是否已经打卡
    if UserCheckin.objects.filter(user=request.user, checkin_id=checkin.id).exists():
            return JsonResponse({"error": "您已经完成该任务"}, status=400)
        
    # 创建打卡记录
    user_checkin = UserCheckin.objects.create(user=request.user, checkin_id=checkin.id,checkin_title=checkin.title)
        
    return JsonResponse({
            "success": True,
            "message": "任务完成！",
            "checkin_record": user_checkin.to_dict()
    })

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
