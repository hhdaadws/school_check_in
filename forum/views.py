from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from .models import Post
from accounts.models import School, User
from accounts.decorators import login_required, admin_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Case, When, IntegerField, Count
import json
import os
import math
import time
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
        
        # 获取分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        
        # 验证参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:  # 限制最大每页数量
            page_size = 10
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 查询帖子总数
        total_posts = Post.objects.filter(school_id=school_id, status='approved').count()
        
        # 查询当前页的帖子
        posts = Post.objects.filter(school_id=school_id, status='approved').order_by('-time')[offset:offset + page_size]
        
        # 获取当前登录用户（如果有的话）
        current_user = getattr(request, 'user', None) if hasattr(request, 'user') else None
        
        # 构造响应数据
        data = {
            'posts': [post.to_dict(user=current_user) for post in posts],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total_posts,
                'total_pages': math.ceil(total_posts / page_size) if total_posts > 0 else 1,
                'has_next': page < math.ceil(total_posts / page_size) if total_posts > 0 else False,
                'has_prev': page > 1
            }
        }
        
        return JsonResponse(data, safe=False)
    except (ValueError, School.DoesNotExist):
        return JsonResponse({"error": "无效的学校ID"}, status=400)

# 搜索帖子
def search_posts(request):
    """搜索帖子API"""
    # 获取搜索参数
    query = request.GET.get('q', '').strip()
    school_id = request.GET.get('school_id')
    
    if not query:
        return JsonResponse({"error": "搜索关键词不能为空"}, status=400)
    
    if not school_id:
        return JsonResponse({"error": "需要提供school_id参数"}, status=400)
    
    try:
        school_id = int(school_id)
        start_time = time.time()
        
        # 获取分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        
        # 验证参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 处理搜索关键词（支持多关键词）
        keywords = [keyword.strip() for keyword in query.split() if keyword.strip()]
        
        # 构建搜索查询
        search_query = Q()
        
        # 为每个关键词构建查询条件
        for keyword in keywords:
            keyword_query = (
                Q(title__icontains=keyword) |
                Q(content__icontains=keyword) |
                Q(author__icontains=keyword)
            )
            search_query &= keyword_query  # AND逻辑：所有关键词都必须匹配
        
        # 基础查询：限制学校和状态
        base_query = Post.objects.filter(
            school_id=school_id,
            status='approved'
        )
        
        # 添加搜索条件
        posts_query = base_query.filter(search_query)
        
        # 计算相关性评分并排序
        posts_query = posts_query.annotate(
            relevance_score=Case(
                # 标题匹配得分最高
                *[When(title__icontains=keyword, then=10) for keyword in keywords],
                # 内容匹配得分中等
                *[When(content__icontains=keyword, then=5) for keyword in keywords],
                # 作者匹配得分较低
                *[When(author__icontains=keyword, then=3) for keyword in keywords],
                default=0,
                output_field=IntegerField()
            )
        ).order_by('-relevance_score', '-time')
        
        # 获取总数
        total_posts = posts_query.count()
        
        # 获取当前页的帖子
        posts = posts_query[offset:offset + page_size]
        
        # 获取当前登录用户
        current_user = getattr(request, 'user', None) if hasattr(request, 'user') else None
        
        # 计算搜索用时
        search_time = time.time() - start_time
        
        # 构造响应数据
        data = {
            'posts': [post.to_dict(user=current_user) for post in posts],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total_posts,
                'total_pages': math.ceil(total_posts / page_size) if total_posts > 0 else 1,
                'has_next': page < math.ceil(total_posts / page_size) if total_posts > 0 else False,
                'has_prev': page > 1
            },
            'search_info': {
                'query': query,
                'keywords': keywords,
                'total_found': total_posts,
                'search_time': f"{search_time:.3f}s",
                'highlight_fields': ['title', 'content', 'author']
            }
        }
        
        return JsonResponse(data, safe=False)
        
    except (ValueError, School.DoesNotExist) as e:
        return JsonResponse({"error": f"参数错误: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"搜索失败: {str(e)}"}, status=500)

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
            margin-bottom: 20px;
        }
        
        .interaction-section {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .post-actions {
            display: flex;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #eee;
            margin-bottom: 20px;
        }
        
        .action-group {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .action-btn {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 8px 12px;
            border: none;
            background: #f5f5f5;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 14px;
        }
        
        .action-btn:hover {
            background: #e6e6e6;
        }
        
        .action-btn.liked {
            background: #f39c12;
            color: white;
        }
        
        .action-btn.liked:hover {
            background: #e67e22;
        }
        
        .comments-section {
            margin-top: 20px;
        }
        
        .comment-form {
            margin-bottom: 20px;
        }
        
        .comment-item {
            background: #f9f9f9;
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }
        
        .comment-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .comment-author {
            font-weight: bold;
            color: #409EFF;
        }
        
        .comment-time {
            color: #999;
            font-size: 12px;
        }
        
        .comment-content {
            line-height: 1.5;
            color: #333;
        }
        
        .comment-reply {
            margin-left: 20px;
            margin-top: 10px;
            border-left: 3px solid #409EFF;
            padding-left: 15px;
        }
        
        .login-tip {
            text-align: center;
            padding: 20px;
            background: #f0f9ff;
            border-radius: 8px;
            margin-bottom: 20px;
            color: #666;
        }
        
        .login-tip a {
            color: #409EFF;
            text-decoration: none;
        }
        
        .login-tip a:hover {
            text-decoration: underline;
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
    <div id="app" class="container">
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
        
        <!-- 交互功能区域 -->
        <div class="interaction-section">
            <!-- 点赞和评论操作 -->
            <div class="post-actions">
                <div class="action-group">
                    <button 
                        v-if="isLoggedIn"
                        class="action-btn" 
                        :class="{ liked: post.user_liked }"
                        @click="toggleLike"
                        :disabled="likeLoading">
                        <i class="el-icon-star-off" v-if="!post.user_liked"></i>
                        <i class="el-icon-star-on" v-else></i>
                        <span>{{ post.user_liked ? '已点赞' : '点赞' }} ({{ post.likes_count || 0 }})</span>
                    </button>
                    <div v-else class="action-btn">
                        <i class="el-icon-star-off"></i>
                        <span>点赞 ({{ post.likes_count || 0 }})</span>
                    </div>
                    
                    <div class="action-btn">
                        <i class="el-icon-chat-line-round"></i>
                        <span>评论 ({{ comments.length }})</span>
                    </div>
                </div>
            </div>
            
            <!-- 评论区域 -->
            <div class="comments-section">
                <h4 style="margin-bottom: 15px;">评论区</h4>
                
                <!-- 登录提示 -->
                <div v-if="!isLoggedIn" class="login-tip">
                    <p>请先<a href="/accounts/">登录</a>后再进行评论和点赞</p>
                </div>
                
                <!-- 评论表单 -->
                <div v-if="isLoggedIn" class="comment-form">
                    <el-input
                        type="textarea"
                        v-model="newComment.content"
                        placeholder="写下你的评论..."
                        :rows="3"
                        maxlength="500"
                        show-word-limit>
                    </el-input>
                    <div style="margin-top: 10px; text-align: right;">
                        <el-button 
                            type="primary" 
                            size="small" 
                            @click="addComment"
                            :loading="commentLoading"
                            :disabled="!newComment.content.trim()">
                            发表评论
                        </el-button>
                    </div>
                </div>
                
                <!-- 评论列表 -->
                <div v-if="comments.length > 0">
                    <div v-for="comment in comments" :key="comment.id" class="comment-item">
                        <div class="comment-header">
                            <span class="comment-author">{{ comment.username }}</span>
                            <span class="comment-time">{{ comment.created_at }}</span>
                        </div>
                        <div class="comment-content">{{ comment.content }}</div>
                        
                        <!-- 回复 -->
                        <div v-if="comment.replies && comment.replies.length > 0">
                            <div v-for="reply in comment.replies" :key="reply.id" class="comment-reply">
                                <div class="comment-header">
                                    <span class="comment-author">{{ reply.username }}</span>
                                    <span class="comment-time">{{ reply.created_at }}</span>
                                </div>
                                <div class="comment-content">{{ reply.content }}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div v-else-if="!commentsLoading" style="text-align: center; color: #999; padding: 20px;">
                    暂无评论，快来发表第一条评论吧！
                </div>
                
                <div v-if="commentsLoading" style="text-align: center; padding: 20px;">
                    <i class="el-icon-loading"></i> 加载评论中...
                </div>
            </div>
        </div>
        
        <div class="back-button">
            <button @click="goBack" class="back-link">返回上页</button>
        </div>
    </div>

    <script>
        new Vue({
            el: '#app',
            data: {
                postId: {{post_id}},
                post: {
                    id: {{post_id}},
                    title: '{{title}}',
                    author: '{{author}}',
                    content: '{{content}}',
                    time: '{{time}}',
                    likes_count: 0,
                    user_liked: false
                },
                comments: [],
                newComment: {
                    content: '',
                    parent_id: null
                },
                isLoggedIn: false,
                currentUser: null,
                likeLoading: false,
                commentLoading: false,
                commentsLoading: false
            },
            mounted() {
                this.checkLoginStatus();
                this.loadPostInteractions();
                this.loadComments();
            },
            methods: {
                checkLoginStatus() {
                    // 检查用户登录状态
                    const user = localStorage.getItem('user');
                    if (user) {
                        try {
                            this.currentUser = JSON.parse(user);
                            this.isLoggedIn = true;
                        } catch (e) {
                            console.error('解析用户信息失败:', e);
                            localStorage.removeItem('user');
                        }
                    }
                },
                
                loadPostInteractions() {
                    // 加载帖子点赞状态
                    if (this.isLoggedIn) {
                        axios.get(`/forum/posts/${this.postId}/like-status/`)
                            .then(response => {
                                this.post.likes_count = response.data.likes_count;
                                this.post.user_liked = response.data.user_liked;
                            })
                            .catch(error => {
                                console.error('加载点赞状态失败:', error);
                            });
                    } else {
                        // 未登录用户只获取点赞数
                        axios.get(`/forum/posts/${this.postId}/`)
                            .then(response => {
                                this.post.likes_count = response.data.likes_count || 0;
                                this.post.user_liked = false;
                            })
                            .catch(error => {
                                console.error('加载帖子信息失败:', error);
                            });
                    }
                },
                
                loadComments() {
                    this.commentsLoading = true;
                    axios.get(`/forum/posts/${this.postId}/comments/`)
                        .then(response => {
                            this.comments = response.data.comments || [];
                            this.commentsLoading = false;
                        })
                        .catch(error => {
                            console.error('加载评论失败:', error);
                            this.commentsLoading = false;
                            this.$message.error('加载评论失败');
                        });
                },
                
                toggleLike() {
                    if (!this.isLoggedIn) {
                        this.$message.warning('请先登录');
                        return;
                    }
                    
                    this.likeLoading = true;
                    
                    axios.post(`/forum/posts/${this.postId}/like/`)
                        .then(response => {
                            if (response.data.success) {
                                this.post.user_liked = response.data.user_liked;
                                this.post.likes_count = response.data.likes_count;
                                this.$message.success(response.data.message);
                            }
                            this.likeLoading = false;
                        })
                        .catch(error => {
                            console.error('点赞操作失败:', error);
                            this.$message.error('操作失败，请重试');
                            this.likeLoading = false;
                        });
                },
                
                addComment() {
                    if (!this.isLoggedIn) {
                        this.$message.warning('请先登录');
                        return;
                    }
                    
                    if (!this.newComment.content.trim()) {
                        this.$message.warning('请输入评论内容');
                        return;
                    }
                    
                    this.commentLoading = true;
                    
                    const commentData = {
                        content: this.newComment.content.trim(),
                        parent_id: this.newComment.parent_id
                    };
                    
                    axios.post(`/forum/posts/${this.postId}/comments/create/`, commentData)
                        .then(response => {
                            if (response.data.success) {
                                this.$message.success('评论发表成功');
                                this.newComment.content = '';
                                this.newComment.parent_id = null;
                                this.loadComments(); // 重新加载评论列表
                            }
                            this.commentLoading = false;
                        })
                        .catch(error => {
                            console.error('发表评论失败:', error);
                            const errorMsg = error.response?.data?.error || '发表评论失败';
                            this.$message.error(errorMsg);
                            this.commentLoading = false;
                        });
                },
                
                goBack() {
                    // 智能返回功能
                    try {
                        // 检查是否有可用的历史记录
                        if (window.history.length > 1 && document.referrer) {
                            // 检查来源是否为本站
                            const referrer = new URL(document.referrer);
                            const currentHost = window.location.host;
                            
                            if (referrer.host === currentHost) {
                                // 来源是本站，使用history.back()
                                window.history.back();
                                return;
                            }
                        }
                        
                        // Fallback：跳转到论坛tab
                        this.goToForumTab();
                        
                    } catch (error) {
                        console.error('返回操作失败:', error);
                        // 出错时的fallback
                        this.goToForumTab();
                    }
                },
                
                goToForumTab() {
                    // 跳转到论坛tab的方法
                    const url = '/accounts/';
                    
                    // 检查用户上次使用的tab，优先返回到论坛，其次是用户上次的tab
                    const lastTab = localStorage.getItem('lastActiveTab');
                    const targetTab = 'forum'; // 默认返回论坛，因为用户是从帖子详情返回的
                    
                    // 使用localStorage来标记要显示的tab
                    localStorage.setItem('activeTab', targetTab);
                    window.location.href = url;
                }
            }
        });
    </script>
</body>
</html>
        """
    
    # 替换模板中的变量
    html_content = template_content.replace('{{title}}', post.title)
    html_content = html_content.replace('{{author}}', post.author)
    html_content = html_content.replace('{{time}}', post.time.strftime('%Y-%m-%d %H:%M'))
    html_content = html_content.replace('{{post_id}}', str(post.id))
    
    # 替换内容时保留换行，但保持原有格式
    html_content = html_content.replace('{{content}}', post.content)
    
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
