"""
自定义权限：仅 admin 角色可访问用户管理接口
"""
from rest_framework import permissions


class IsAdminRole(permissions.BasePermission):
    """仅 admin 角色可访问"""

    message = "仅管理员可操作用户管理功能"

    def has_permission(self, request, view):
        """校验全局权限：用户已登录 + 角色是admin"""
        print(f"当前用户: {request.user}, 认证状态: {request.user.is_authenticated}, 角色: {getattr(request.user, 'role', 'N/A')}")
        return request.user and request.user.is_authenticated and request.user.is_admin

    def has_object_permission(self, request, view, obj):
        """校验对象权限: 禁止admin删除自己"""
        if request.method == "DELETE" and obj.id == request.user.id:
            self.message = "禁止删除当前登录的管理员"
            return False
        return True
