from django.urls import path
from . import views

urlpatterns = [
    # API 路由
    path('api/schools/', views.get_schools, name='get_schools'),
    path('posts/', views.get_posts, name='get_posts'),
    path('posts/create/', views.create_post, name='create_post'),
    path('posts/user/', views.get_user_posts, name='get_user_posts'),
    path('posts/<int:post_id>/', views.get_post_detail, name='get_post_detail'),
    path('posts/<int:post_id>/review/', views.review_post, name='review_post'),
    path('posts/pending/', views.get_pending_posts, name='get_pending_posts'),
    path('posts/generate-html/', views.generate_post_html, name='generate_post_html'),
] 