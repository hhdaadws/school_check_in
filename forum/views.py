from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from .models import Post
from accounts.models import School, User
from accounts.decorators import login_required, admin_required
from django.views.decorators.csrf import csrf_exempt
import json
import os
from django.conf import settings
from django.utils import timezone

# Create your views here.

# 获取指定学校的所有帖子
def get_posts(request):
    """获取指定学校的帖子（仅展示已审核通过的）"""
    school_id = request.GET.get('school_id')
    if not school_id:
        return JsonResponse({"error": "需要提供school_id参数"}, status=400)
    
    try:
        school_id = int(school_id)
        # 只返回已审核通过的帖子
        posts = Post.objects.filter(school_id=school_id, status='approved').order_by('-time')
        # 获取当前登录用户（如果有的话）
        current_user = getattr(request, 'user', None) if hasattr(request, 'user') else None
        data = [post.to_dict(user=current_user) for post in posts]
        return JsonResponse(data, safe=False)
    except (ValueError, School.DoesNotExist):
        return JsonResponse({"error": "无效的学校ID"}, status=400)

# 管理员获取待审核帖子
@csrf_exempt
@admin_required
def get_pending_posts(request):
    """获取所有待审核的帖子"""
    status = request.GET.get('status', 'pending')
    if status not in ['pending', 'approved', 'rejected', 'all']:
        status = 'pending'
    
    try:
        if status == 'all':
            posts = Post.objects.all().order_by('-time')
        else:
            posts = Post.objects.filter(status=status).order_by('-time')
        current_user = getattr(request, 'user', None) if hasattr(request, 'user') else None
        data = [post.to_dict(user=current_user) for post in posts]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": f"获取帖子失败: {str(e)}"}, status=500)

# 管理员审核帖子
@csrf_exempt
@admin_required
def review_post(request, post_id):
    """审核帖子"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        post = Post.objects.get(id=post_id)
        data = json.loads(request.body)
        status = data.get('status')
        reject_reason = data.get('reject_reason', '')
        
        if status not in ['approved', 'rejected']:
            return JsonResponse({"error": "无效的审核状态"}, status=400)
        
        post.status = status
        post.reviewed_by = request.user
        post.reviewed_time = timezone.now()
        
        if status == 'rejected':
            post.reject_reason = reject_reason
            
        post.save()
        
        # 如果审核通过，生成HTML页面
        if status == 'approved':
            create_post_html(post)
            
        current_user = getattr(request, 'user', None) if hasattr(request, 'user') else None
        return JsonResponse({
            "success": True,
            "message": "审核完成",
            "post": post.to_dict(user=current_user)
        })
    except Post.DoesNotExist:
        return JsonResponse({"error": "帖子不存在"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的JSON数据"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"审核失败: {str(e)}"}, status=500)

def get_schools(request):
    """获取所有学校信息"""
    schools = School.objects.all()
    data = [school.to_dict() for school in schools]
    return JsonResponse(data, safe=False)

# 获取帖子详情
def get_post_detail(request, post_id):
    """获取帖子详情"""
    try:
        post = Post.objects.get(id=post_id)
        
        # 检查帖子状态和用户权限
        is_staff = hasattr(request, 'user') and request.user and getattr(request.user, 'is_staff', False)
        is_author = hasattr(request, 'user') and request.user and request.user.id and post.user and post.user.id == request.user.id
        
        # 如果帖子未审核通过且当前用户不是管理员或帖子作者，则不允许查看
        if post.status != 'approved' and not (is_staff or is_author):
            return JsonResponse({"error": "该帖子尚未审核通过"}, status=403)
        
        current_user = getattr(request, 'user', None) if hasattr(request, 'user') else None
        return JsonResponse(post.to_dict(user=current_user))
    except Post.DoesNotExist:
        return JsonResponse({"error": "帖子不存在"}, status=404)

# 创建新帖子
@csrf_exempt
@login_required
def create_post(request):
    """创建新帖子"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        # 导入审核服务
        from .moderation import moderation_service
        
        data = json.loads(request.body)
        title = data.get('title')
        content = data.get('content', '')
        school_id = data.get('school_id')
        
        if not all([title, school_id]):
            return JsonResponse({"error": "标题和学校ID不能为空"}, status=400)
        
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return JsonResponse({"error": "指定的学校不存在"}, status=400)
        
        # 🎯 新增：内容审核检测
        is_valid, error_message, violations_info = moderation_service.check_post(
            user=request.user,
            title=title,
            content=content
        )
        
        # 如果检测到违规内容，直接拒绝发布
        if not is_valid:
            return JsonResponse({
                "error": error_message,
                "violation_details": violations_info
            }, status=400)
        
        # 通过审核，直接发布帖子
        post = Post.objects.create(
            title=title,
            content=content,
            school=school,
            author=request.user.username,
            user=request.user,
            status='approved',  # 🎯 修改：自动审核通过，直接发布
            auto_approved=True,  # 标记为自动审核通过
            moderation_result='auto_approved'  # 记录审核结果
        )
        
        # 如果帖子审核通过，生成HTML页面
        create_post_html(post)
        
        return JsonResponse({
            "success": True,
            "message": "发布成功！帖子已通过自动审核",
            "post": post.to_dict(user=request.user)
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的JSON数据"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"发布失败: {str(e)}"}, status=500)

@csrf_exempt
@login_required
def generate_post_html(request):
    """生成帖子HTML页面"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        data = json.loads(request.body)
        post_id = data.get('post_id')
        
        if not post_id:
            return JsonResponse({"error": "帖子ID不能为空"}, status=400)
        
        try:
            post = Post.objects.get(id=post_id)
            
            # 只有已审核通过的帖子才能生成HTML页面
            if post.status != 'approved':
                return JsonResponse({"error": "只有已审核通过的帖子才能生成HTML页面"}, status=403)
                
        except Post.DoesNotExist:
            return JsonResponse({"error": "指定的帖子不存在"}, status=400)
        
        # 创建帖子详情页
        create_post_html(post)
        
        return JsonResponse({
            "success": True,
            "message": "帖子详情页生成成功",
            "html_path": f"/post_{post.id}.html"
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的JSON数据"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"生成帖子详情页失败: {str(e)}"}, status=500)

def serve_post_html(request, post_id):
    """提供帖子HTML页面"""
    html_file_path = os.path.join(settings.BASE_DIR, 'htmls', f'post_{post_id}.html')
    
    try:
        post = Post.objects.get(id=post_id)
        # 检查帖子状态和用户权限
        is_staff = hasattr(request, 'user') and request.user and getattr(request.user, 'is_staff', False)
        is_author = hasattr(request, 'user') and request.user and request.user.id and post.user and post.user.id == request.user.id
        
        # 如果帖子未审核通过且当前用户不是管理员或帖子作者，则不允许查看
        if post.status != 'approved' and not (is_staff or is_author):
            return HttpResponse("该帖子尚未审核通过", status=403)
            
        if not os.path.exists(html_file_path):
            # 如果帖子已审核通过，则生成HTML
            if post.status == 'approved':
                create_post_html(post)
                if not os.path.exists(html_file_path):
                    raise Http404("帖子页面生成失败")
            else:
                raise Http404("帖子未审核通过，无法查看")
    except Post.DoesNotExist:
        raise Http404("帖子不存在")
    
    # 读取文件内容
    with open(html_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    return HttpResponse(content, content_type='text/html')

def create_post_html(post):
    """创建帖子HTML页面"""
    # 只为已审核通过的帖子创建HTML文件
    if post.status != 'approved':
        return None
        
    # 确保htmls目录存在
    html_dir = os.path.join(settings.BASE_DIR, 'htmls')
    if not os.path.exists(html_dir):
        os.makedirs(html_dir)
    
    # 创建帖子详情页HTML文件路径
    html_file_path = os.path.join(html_dir, f'post_{post.id}.html')
    
    # 读取帖子模板（如果没有则创建一个基本模板）
    template_path = os.path.join(settings.BASE_DIR, 'htmls', 'post_template.html')
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()
    else:
        # 基本模板
        template_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}} - 校园论坛</title>
    <!-- 引入Vue.js和Axios -->
    <script src="https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <!-- 引入Element UI -->
    <link rel="stylesheet" href="https://unpkg.com/element-ui/lib/theme-chalk/index.css">
    <script src="https://unpkg.com/element-ui/lib/index.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .post-header {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .post-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        
        .post-meta {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            color: #999;
            margin-bottom: 10px;
        }
        
        .post-content {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            line-height: 1.6;
            white-space: pre-wrap;
        }
        
        .back-button {
            margin-top: 20px;
            text-align: center;
        }
        
        .back-link {
            display: inline-block;
            padding: 10px 20px;
            background-color: #409EFF;
            color: white;
            border-radius: 4px;
            text-decoration: none;
            font-weight: bold;
        }
        
        .back-link:hover {
            background-color: #66b1ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="post-header">
            <div class="post-title">{{title}}</div>
            <div class="post-meta">
                <span>作者: {{author}}</span>
                <span>发布时间: {{time}}</span>
            </div>
        </div>
        <div class="post-content">
            {{content}}
        </div>
        <div class="back-button">
            <a href="/accounts/" class="back-link">返回首页</a>
        </div>
    </div>
</body>
</html>
        """
    
    # 替换模板中的变量
    html_content = template_content.replace('{{title}}', post.title)
    html_content = html_content.replace('{{author}}', post.author)
    html_content = html_content.replace('{{time}}', post.time.strftime('%Y-%m-%d %H:%M'))
    
    # 替换内容时保留换行
    content_with_breaks = post.content.replace('\n', '<br>')
    html_content = html_content.replace('{{content}}', content_with_breaks)
    
    try:
        # 写入HTML文件
        with open(html_file_path, 'w', encoding='utf-8') as file:
            file.write(html_content)
        
        print(f"成功生成帖子HTML文件: {html_file_path}")
    except Exception as e:
        print(f"生成帖子HTML文件失败: {str(e)}")
    
    return html_file_path

# 获取用户自己的帖子
@csrf_exempt
@login_required
def get_user_posts(request):
    """获取当前用户发布的所有帖子，包括待审核的"""
    try:
        # 额外的安全检查
        if not request.user or not hasattr(request.user, 'id') or request.user.id is None:
            return JsonResponse({"error": "用户未登录"}, status=401)
            
        posts = Post.objects.filter(user=request.user).order_by('-time')
        data = [post.to_dict(user=request.user) for post in posts]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": f"获取帖子失败: {str(e)}"}, status=500)

# ========== 点赞相关API ==========

@csrf_exempt
@login_required
def toggle_post_like(request, post_id):
    """切换帖子点赞状态（点赞/取消点赞）"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        from .models import Post, PostLike
        
        post = Post.objects.get(id=post_id, status='approved')
        user = request.user
        
        # 检查是否已经点赞
        like, created = PostLike.objects.get_or_create(
            post=post,
            user=user,
            defaults={'created_at': timezone.now()}
        )
        
        if not created:
            # 如果已存在，则取消点赞
            like.delete()
            action = 'unliked'
            message = '取消点赞成功'
        else:
            # 如果不存在，则点赞
            action = 'liked'
            message = '点赞成功'
        
        # 获取最新的点赞数
        likes_count = post.likes.count()
        
        return JsonResponse({
            "success": True,
            "action": action,
            "message": message,
            "likes_count": likes_count,
            "user_liked": action == 'liked'
        })
        
    except Post.DoesNotExist:
        return JsonResponse({"error": "帖子不存在或未审核通过"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"操作失败: {str(e)}"}, status=500)


@csrf_exempt
def get_post_likes(request, post_id):
    """获取帖子的点赞用户列表"""
    try:
        from .models import Post, PostLike
        
        post = Post.objects.get(id=post_id, status='approved')
        
        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # 获取点赞列表
        likes = PostLike.objects.filter(post=post).order_by('-created_at')
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        likes_page = likes[start:end]
        
        data = {
            'total': likes.count(),
            'page': page,
            'page_size': page_size,
            'likes': [like.to_dict() for like in likes_page]
        }
        
        return JsonResponse(data)
        
    except Post.DoesNotExist:
        return JsonResponse({"error": "帖子不存在或未审核通过"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"获取点赞列表失败: {str(e)}"}, status=500)


@csrf_exempt
@login_required
def get_post_like_status(request, post_id):
    """获取当前用户对帖子的点赞状态"""
    try:
        from .models import Post, PostLike
        
        post = Post.objects.get(id=post_id, status='approved')
        user = request.user
        
        user_liked = PostLike.objects.filter(post=post, user=user).exists()
        likes_count = post.likes.count()
        
        return JsonResponse({
            "user_liked": user_liked,
            "likes_count": likes_count
        })
        
    except Post.DoesNotExist:
        return JsonResponse({"error": "帖子不存在或未审核通过"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"获取点赞状态失败: {str(e)}"}, status=500)


# ========== 评论相关API ==========

@csrf_exempt
@login_required
def create_post_comment(request, post_id):
    """发表评论"""
    if request.method != 'POST':
        return JsonResponse({"error": "只支持POST请求"}, status=405)
    
    try:
        from .models import Post, PostComment
        
        post = Post.objects.get(id=post_id, status='approved')
        user = request.user
        
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        parent_id = data.get('parent_id')
        
        if not content:
            return JsonResponse({"error": "评论内容不能为空"}, status=400)
        
        if len(content) > 1000:
            return JsonResponse({"error": "评论内容不能超过1000个字符"}, status=400)
        
        # 检查父评论是否存在
        parent = None
        if parent_id:
            try:
                parent = PostComment.objects.get(id=parent_id, post=post, is_deleted=False)
            except PostComment.DoesNotExist:
                return JsonResponse({"error": "父评论不存在"}, status=400)
        
        # 🎯 新增：内容审核检测
        from .moderation import moderation_service
        is_valid, violations_list = moderation_service.check_text(content)
        
        if not is_valid:
            # 生成错误信息
            violation_categories = [v['category'] for v in violations_list]
            error_message = f"包含{', '.join(set(violation_categories))}相关内容"
            
            return JsonResponse({
                "error": f"评论内容包含违规内容：{error_message}",
                "violation_details": violations_list
            }, status=400)
        
        # 创建评论
        comment = PostComment.objects.create(
            post=post,
            user=user,
            parent=parent,
            content=content
        )
        
        # 返回评论数据
        comment_data = comment.to_dict(include_replies=False)
        comment_data['is_author'] = True  # 当前用户是评论作者
        
        return JsonResponse({
            "success": True,
            "message": "评论发表成功",
            "comment": comment_data,
            "comments_count": post.comments.filter(is_deleted=False).count()
        })
        
    except Post.DoesNotExist:
        return JsonResponse({"error": "帖子不存在或未审核通过"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的JSON数据"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"发表评论失败: {str(e)}"}, status=500)


@csrf_exempt
def get_post_comments(request, post_id):
    """获取帖子的评论列表"""
    try:
        from .models import Post, PostComment
        
        post = Post.objects.get(id=post_id, status='approved')
        
        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        
        # 获取顶级评论（没有父评论的评论）
        comments = PostComment.objects.filter(
            post=post, 
            parent=None, 
            is_deleted=False
        ).order_by('-created_at')
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        comments_page = comments[start:end]
        
        # 获取当前用户
        current_user = getattr(request, 'user', None) if hasattr(request, 'user') else None
        
        # 转换为字典格式
        comments_data = []
        for comment in comments_page:
            comment_dict = comment.to_dict(include_replies=True)
            # 设置是否为当前用户的评论
            comment_dict['is_author'] = (current_user and 
                                       hasattr(current_user, 'id') and 
                                       current_user.id == comment.user.id)
            # 设置回复的作者标识
            if 'replies' in comment_dict:
                for reply in comment_dict['replies']:
                    reply['is_author'] = (current_user and 
                                        hasattr(current_user, 'id') and 
                                        current_user.id == reply.get('user_id'))
            comments_data.append(comment_dict)
        
        data = {
            'total': comments.count(),
            'page': page,
            'page_size': page_size,
            'comments': comments_data
        }
        
        return JsonResponse(data)
        
    except Post.DoesNotExist:
        return JsonResponse({"error": "帖子不存在或未审核通过"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"获取评论列表失败: {str(e)}"}, status=500)


@csrf_exempt
@login_required
def update_comment(request, comment_id):
    """编辑评论（仅作者可编辑）"""
    if request.method != 'PUT':
        return JsonResponse({"error": "只支持PUT请求"}, status=405)
    
    try:
        from .models import PostComment
        
        comment = PostComment.objects.get(id=comment_id, is_deleted=False)
        user = request.user
        
        # 检查是否为评论作者
        if comment.user.id != user.id:
            return JsonResponse({"error": "只能编辑自己的评论"}, status=403)
        
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({"error": "评论内容不能为空"}, status=400)
        
        if len(content) > 1000:
            return JsonResponse({"error": "评论内容不能超过1000个字符"}, status=400)
        
        # 🎯 内容审核检测
        from .moderation import moderation_service
        is_valid, violations_list = moderation_service.check_text(content)
        
        if not is_valid:
            # 生成错误信息
            violation_categories = [v['category'] for v in violations_list]
            error_message = f"包含{', '.join(set(violation_categories))}相关内容"
            
            return JsonResponse({
                "error": f"评论内容包含违规内容：{error_message}",
                "violation_details": violations_list
            }, status=400)
        
        # 更新评论
        comment.content = content
        comment.save()
        
        # 返回更新后的评论数据
        comment_data = comment.to_dict(include_replies=False)
        comment_data['is_author'] = True
        
        return JsonResponse({
            "success": True,
            "message": "评论更新成功",
            "comment": comment_data
        })
        
    except PostComment.DoesNotExist:
        return JsonResponse({"error": "评论不存在"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "无效的JSON数据"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"更新评论失败: {str(e)}"}, status=500)


@csrf_exempt
@login_required
def delete_comment(request, comment_id):
    """删除评论（软删除，仅作者和管理员可删除）"""
    if request.method != 'DELETE':
        return JsonResponse({"error": "只支持DELETE请求"}, status=405)
    
    try:
        from .models import PostComment
        
        comment = PostComment.objects.get(id=comment_id, is_deleted=False)
        user = request.user
        
        # 检查权限：评论作者或管理员
        is_author = comment.user.id == user.id
        is_admin = getattr(user, 'is_staff', False)
        
        if not (is_author or is_admin):
            return JsonResponse({"error": "没有权限删除此评论"}, status=403)
        
        # 软删除评论
        comment.is_deleted = True
        comment.save()
        
        # 更新帖子的评论数
        post = comment.post
        comments_count = post.comments.filter(is_deleted=False).count()
        
        return JsonResponse({
            "success": True,
            "message": "评论删除成功",
            "comments_count": comments_count
        })
        
    except PostComment.DoesNotExist:
        return JsonResponse({"error": "评论不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"删除评论失败: {str(e)}"}, status=500)
