#!/usr/bin/env python
import os
import sys
import subprocess

def main():
    # 设置环境变量
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Arx.settings')
    
    # 确保工作目录正确
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查依赖项
    try:
        import django
        print(f"Django 版本: {django.__version__}")
        import channels
        print(f"Channels 版本: {channels.__version__}")
        import daphne
        print(f"Daphne 版本: {daphne.__file__}")
    except ImportError as e:
        print(f"错误: {e}")
        print("请确保已安装所有必要的依赖项: django, channels, daphne")
        return
    
    # 先收集静态文件
    print("收集静态文件...")
    subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"])
    
    # 检查数据库迁移
    print("检查数据库迁移...")
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"])
    
    # 运行daphne服务器
    print("启动Daphne服务器...")
    host = "0.0.0.0"
    port = "8000"
    print(f"服务器将在 http://{host}:{port} 运行")
    
    # 使用subprocess模块运行daphne命令
    daphne_cmd = ["daphne", "-b", host, "-p", port, "Arx.asgi:application"]
    print(f"执行命令: {' '.join(daphne_cmd)}")
    subprocess.run(daphne_cmd)

if __name__ == "__main__":
    main() 