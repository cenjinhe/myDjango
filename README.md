# myDjango
# 可能遇到的问题
## 问题：
自定义 User 模型和 Django 内置 auth.User 模型的 groups/user_permissions 字段，
给 Group/Permission 模型生成了同名的反向访问器 user_set，导致 Django 无法区分
## 解决步骤：
这个方案的核心是：确保 Django 只识别你的自定义 User 模型，完全屏蔽内置 auth.User，从根源上消除冲突
（适合开发初期，无数据丢失风险）
1. 进入项目根目录（确保激活虚拟环境）
cd /你的Django项目路径

2. 删除所有 app 下 migrations 目录中除 __init__.py 外的文件
 （手动删，或执行以下命令，注意：仅开发环境执行！）
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

3. 删除数据库文件（sqlite3 场景）
rm -f db.sqlite3

4. （可选）删除数据库缓存文件（若有）
rm -f db.sqlite3-journal

5. 检查settings.py
    a.注册你的自定义用户 app（比如名为 users）
    INSTALLED_APPS = [
        ...
        'django.contrib.staticfiles',
        'users',  # 你的自定义用户 app，必须放在前面
    ]
    
    b.核心配置：指定唯一的用户模型（格式：app名.模型名）
    必须在首次 migrate 前配置，这是 Django 的硬性要求！
    AUTH_USER_MODEL = "users.User"
    
6.重新执行迁移，重建数据库

    6.1. 生成新的迁移文件（此时 Django 会以你的 User 为核心）
    python manage.py makemigrations

    6.2. 执行迁移（创建新的数据库表，无内置 auth.User 冲突）
    python manage.py migrate

    6.3. 创建超级用户（用于登录后台，验证模型是否生效）
    python manage.py createsuperuser