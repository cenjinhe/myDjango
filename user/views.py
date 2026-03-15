from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
    action,
)
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework.throttling import AnonRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, filters, status
from .serializers import UserSerializer
from .permissions import IsAdminRole
from config import get_logger
import jwt
from django.conf import settings
import re
from typing import Dict, Any, Optional

# 配置日志
logger = get_logger(__file__)

from user.models import User

# 常量定义
PHONE_REGEX = r"^1[3-9]\d{9}$"
MIN_PASSWORD_LENGTH = 6
DEFAULT_AVATAR = "https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif"


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> Optional[Response]:
    """验证必填字段"""
    for field in required_fields:
        if not data.get(field, "").strip():
            return Response(
                {"message": f"{field} is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
    return None


def validate_phone(phone: str) -> Optional[Response]:
    """验证手机号格式"""
    if phone and not re.match(PHONE_REGEX, phone):
        return Response(
            {"message": "phone format is invalid"},
            status=status.HTTP_400_BAD_REQUEST
        )
    return None


def validate_password_strength(password: str) -> Optional[Response]:
    """验证密码强度"""
    if len(password) < MIN_PASSWORD_LENGTH:
        return Response(
            {"message": f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def user_register(request) -> Response:
    """
    用户注册接口
    """
    try:
        data = request.data
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        phone = data.get("phone", "").strip()
    except Exception as e:
        logger.error(f"注册接口解析参数失败: {str(e)}")
        return Response(
            {"message": "Invalid request data format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 验证必填字段
    validation_error = validate_required_fields(data, ["username", "password"])
    if validation_error:
        return validation_error

    # 验证密码强度
    validation_error = validate_password_strength(password)
    if validation_error:
        return validation_error

    # 验证手机号
    validation_error = validate_phone(phone)
    if validation_error:
        return validation_error

    # 唯一性校验
    try:
        if User.objects.filter(username=username).exists():
            logger.warning(f"注册失败: 用户名已存在 - {username}")
            return Response(
                {"message": "username already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if phone and User.objects.filter(phone=phone).exists():
            logger.warning(f"注册失败: 手机号已存在 - {phone}")
            return Response(
                {"message": "phone already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 创建用户
        hashed_password = make_password(password)
        user = User.objects.create(
            username=username,
            password=hashed_password,
            phone=phone if phone else None,
        )

        logger.info(f"用户注册成功 - 用户名: {username} | 用户ID: {user.id}")
        return Response(
            {
                "message": "Register successful",
                "user_id": user.id,
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        logger.error(f"注册接口创建用户异常: {str(e)} | 用户名: {username}")
        return Response(
            {"message": "Server internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def user_login(request) -> Response:
    """
    用户登录接口 (集成 JWT)
    """
    try:
        data = request.data
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
    except Exception as e:
        logger.error(f"登录接口解析参数失败: {str(e)}")
        return Response(
            {"message": "Invalid request data format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 验证必填字段
    validation_error = validate_required_fields(data, ["username", "password"])
    if validation_error:
        return validation_error

    # 查询用户
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warning(f"登录失败: 用户不存在 - 用户名: {username}")
        return Response(
            {"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"登录接口查询用户异常: {str(e)} | 用户名: {username}")
        return Response(
            {"message": "Server internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 验证密码并生成 JWT Token
    if check_password(password, user.password):
        refresh = RefreshToken.for_user(user)

        logger.info(f"用户登录成功 - 用户名: {username} | 用户ID: {user.id}")
        return Response(
            {
                "message": "Login successful",
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
                "user_info": {
                    "user_id": user.id,
                    "username": user.username,
                    "phone": user.phone if hasattr(user, "phone") else None,
                },
            },
            status=status.HTTP_200_OK,
        )
    else:
        logger.warning(f"登录失败: 密码错误 - 用户名: {username}")
        return Response(
            {"message": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def user_logout(request) -> Response:
    """
    用户登出接口 (JWT 黑名单实现)
    """
    try:
        refresh_token = request.data.get("refresh", "").strip()
        if not refresh_token:
            return Response(
                {"message": "refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = RefreshToken(refresh_token)
        token.blacklist()

        logger.info(f"用户登出成功 - 用户名: {request.user.username}")
        return Response(
            {"message": "Logout successful"},
            status=status.HTTP_200_OK
        )

    except (InvalidToken, TokenError) as e:
        logger.warning(f"登出失败: 无效的 Refresh Token - {str(e)} | 用户: {request.user.username}")
        return Response(
            {"message": "Invalid refresh token"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        logger.error(f"登出接口异常 - {str(e)} | 用户: {request.user.username}")
        return Response(
            {"message": "Server internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_info(request) -> Response:
    """
    获取用户信息
    """
    token = request.GET.get("token")

    if not token:
        logger.warning("获取用户信息失败:Token参数缺失")
        return Response(
            {"detail": "Token参数缺失,请在URL中传入token参数"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        UntypedToken(token)

        decoded_token = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=(
                [settings.SIMPLE_JWT["ALGORITHM"]]
                if hasattr(settings, "SIMPLE_JWT")
                else ["HS256"]
            ),
            options={"verify_signature": True},
        )
        user_id = decoded_token.get("user_id")

        user = User.objects.get(id=user_id)

        user_roles = (
            [user.role] if hasattr(user, "role") else ["viewer"]
        )
        response_data = {
            "username": user.username,
            "roles": user_roles,
            "introduction": f"I am {user.username}",
            "avatar": (
                user.avatar
                if hasattr(user, "avatar")
                else DEFAULT_AVATAR
            ),
            "name": user.username,
        }

        logger.info(f"用户{user.username} (ID:{user_id}) 成功获取个人信息")
        return Response(response_data, status=status.HTTP_200_OK)

    except (
        InvalidToken,
        TokenError,
        jwt.ExpiredSignatureError,
        jwt.InvalidSignatureError,
    ) as e:
        logger.error(
            f"Token校验失败:{str(e)},Token值:{token[:20]}..."
        )
        return Response(
            {"detail": "Token无效或已过期,请重新登录"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    except User.DoesNotExist:
        logger.error(
            f"Token对应的用户不存在,user_id:{decoded_token.get('user_id') if 'decoded_token' in locals() else '未知'}"
        )
        return Response(
            {"detail": "Token对应的用户不存在"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(
            f"获取用户信息异常:{str(e)}", exc_info=True
        )
        return Response(
            {"detail": "服务器内部错误,获取用户信息失败"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class UserViewSet(viewsets.ModelViewSet):
    """用户管理视图集: CRUD + 批量删除"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["role"]
    search_fields = ["username", "phone", "email"]
    ordering_fields = ["created_at", "updated_at"]

    def destroy(self, request, *args, **kwargs) -> Response:
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"msg": "删除用户成功"}, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=False)
    def batch_delete(self, request) -> Response:
        """批量删除用户"""
        user_ids = request.data.get("ids", [])
        if not user_ids:
            return Response(
                {"msg": "请选择要删除的用户"}, status=status.HTTP_400_BAD_REQUEST
            )
        user_ids = [uid for uid in user_ids if uid != request.user.id]
        deleted_count, _ = User.objects.filter(id__in=user_ids).delete()
        return Response(
            {"msg": f"成功删除{deleted_count}个用户"}, status=status.HTTP_200_OK
        )
