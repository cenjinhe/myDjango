"""
用户序列化器
"""
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器(CRUD)"""

    # 密码仅写入，不返回
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        error_messages={
            "required": "密码不能为空",
            "min_length": "密码长度不能少于6位",
        },
    )
    # 角色显示名称(只读)
    role_name = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "email",
            "role",
            "role_name",
            "phone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "role_name"]  # 只读字段

    def validate_password(self, value):
        """密码校验：新增时必填，编辑时可选(不填则不更新)"""
        # 编辑场景(instance存在)且密码为空 → 不校验，使用原密码
        if self.instance and not value:
            return self.instance.password
        # 新增场景或编辑时改密码 → 加密
        return make_password(value)

    def create(self, validated_data):
        """创建用户：自动加密密码"""
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新用户：密码为空则不更新"""
        if "password" in validated_data and not validated_data["password"]:
            del validated_data["password"]
        return super().update(instance, validated_data)
