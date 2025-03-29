"""
URL configuration for Arx project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from forum.views import serve_post_html
from admin_center.views import admin_link

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('', lambda request: redirect('accounts:home_page'), name='root'),
    path('forum/', include(('forum.urls', 'forum'), namespace='forum')),
    path('checkin/', include(('checkin.urls', 'checkin'), namespace='checkin')),
    path('admin_center/', include(('admin_center.urls', 'admin_center'), namespace='admin_center')),

    
    # 处理帖子HTML文件的路由
    re_path(r'^post_(?P<post_id>\d+)\.html$', serve_post_html, name='post_detail_html'),
]
