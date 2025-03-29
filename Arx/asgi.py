"""
ASGI config for Arx project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from django.conf import settings

# 确保在导入任何Django模块前设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Arx.settings')
django.setup()

# 在设置环境变量后再导入其他模块
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from chat.routing import websocket_urlpatterns

# 获取Django ASGI应用
http_application = get_asgi_application()

# 配置协议路由
application = ProtocolTypeRouter({
    "http": http_application,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
