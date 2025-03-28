# Arx 项目使用指南

## 技术栈

### 后端
- **Python 3.11**: 项目的主要编程语言
- **Django**: Web框架，提供ORM、视图、模板系统等
- **JWT (JSON Web Tokens)**: 用于无状态身份验证

### 前端
- **HTML5/CSS3**: 网页结构和样式
- **Vue.js 2.6+**: 渐进式JavaScript框架，用于构建用户界面
- **Element UI**: 基于Vue的组件库，提供丰富的UI组件
- **Axios**: 基于Promise的HTTP客户端，用于浏览器和Node.js

## 环境配置

### 系统要求
- 推荐使用虚拟环境管理依赖

### 安装步骤

1. 克隆项目到本地
```bash
git clone [项目仓库URL]
cd Arx
```

2. 创建虚拟环境并激活
```bash
# Windows
python -m venv venv
venv\Scripts\activate

```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 执行数据库迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

5. 创建超级用户（可选，用于管理员访问）
```bash
python manage.py createsuperuser
```

6. 启动开发服务器
```bash
python manage.py runserver
```

7. 访问网站
- 主页: http://127.0.0.1:8000/
- 管理员页面: http://127.0.0.1:8000/admin/

## 项目结构说明

### 目录结构
- `Arx/`: Django项目配置目录
- `accounts/`: 用户账户管理应用
- `htmls/`: 模板文件目录
- `static/`: 静态文件目录

### 核心功能模块
- 用户注册/登录
- JWT令牌身份验证
- 用户资料管理
- 受保护的API路由

## 开发指南

### 添加新功能
1. 在相应的应用中创建模型(models.py)
2. 创建视图函数(views.py)
3. 配置URL路由(urls.py)
4. 创建或修改模板文件(htmls/)
5. 添加静态文件(static/)

### 身份验证流程
1. 用户通过前端表单登录
2. 后端验证凭据并生成JWT令牌
3. 前端保存令牌到localStorage
4. 用户访问受保护资源时，前端在请求头中发送令牌
5. 后端中间件验证令牌并授权访问

## 部署说明

### 生产环境配置
1. 修改`settings.py`中的配置:
   - 设置`DEBUG = False`
   - 配置`ALLOWED_HOSTS`
   - 配置适当的数据库
   - 设置`SECRET_KEY`为环境变量

2. 收集静态文件:
```bash
python manage.py collectstatic
```

3. 使用WSGI服务器(如Gunicorn):
```bash
gunicorn Arx.wsgi:application
```

4. 配置Nginx作为反向代理



## 常见问题与解决方案

1. **静态文件无法加载**
   - 检查`STATIC_URL`和`STATICFILES_DIRS`配置
   - 确认静态文件是否放在正确位置

2. **Django模板与Vue.js语法冲突**
   - 直接读取HTML文件

## 联系与支持

如有问题或建议，请联系项目维护者。 