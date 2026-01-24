from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _  # 国际化支持（可选）
from django.utils import timezone


# Django 内置的 AbstractUser 已经封装了用户名、密码、邮箱、权限等核心字段，在此基础上扩展能减少重复开发，且兼容 Django 自带的认证系统。
class User(AbstractUser):
    """
    扩展 Django 内置用户模型，新增业务所需字段
    核心特性：保留用户名、密码、邮箱等默认字段，新增手机号、头像、性别等自定义字段
    """
    # 1. 新增核心业务字段（根据你的需求调整）
    # 手机号：唯一索引，允许为空（若需强制填写，去掉 null=True, blank=True）
    phone = models.CharField(
        verbose_name=_("手机号"),
        max_length=11,
        unique=True,
        null=True,
        blank=True,
        help_text="请输入11位手机号"
    )
    # 状态：布尔值，标记是否激活（默认激活）
    is_active = models.BooleanField(
        verbose_name=_("是否激活"),
        default=True,
        help_text="取消勾选则用户无法登录"
    )
    # 额外字段：创建时间、更新时间（自动维护）
    created_at = models.DateTimeField(
        verbose_name=_("创建时间"),
        default=timezone.now,
        editable=False  # 不允许在后台编辑
    )
    updated_at = models.DateTimeField(
        verbose_name=_("更新时间"),
        auto_now=True  # 每次保存自动更新为当前时间
    )

    # 2. 元数据配置（优化后台显示和数据库性能）
    class Meta:
        db_table = "user"                       # 数据库表名（默认是 app名_模型名，这里自定义）
        ordering = ["-created_at"]              # 默认按创建时间倒序排列
        indexes = [
            models.Index(fields=["phone"]),     # 给手机号加索引，提升查询速度
            models.Index(fields=["username"]),  # 给用户名加索引
        ]

    # 3. 自定义方法（增强模型功能）
    def __str__(self):
        """后台显示用户名，而非对象内存地址"""
        return self.username

    def get_full_name(self):
        """重写内置方法，返回用户名（可扩展为返回真实姓名）"""
        return f"{self.username}"

    def save(self, *args, **kwargs):
        """重写保存方法：可添加自定义逻辑（比如手机号去空格）"""
        if self.phone:
            self.phone = self.phone.strip()  # 手机号去除首尾空格
        super().save(*args, **kwargs)
