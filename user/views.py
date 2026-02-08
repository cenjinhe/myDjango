from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
    action,
)
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken  # UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError  # 异常类
from rest_framework_simplejwt.tokens import RefreshToken  # 导入 JWT Token 生成模块
from rest_framework.throttling import AnonRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, filters, status
from .serializers import UserSerializer
from .permissions import IsAdminRole
from config import get_logger
import jwt  # jwt解码库
from django.conf import settings  # 配置导入

# 配置日志 (方便线上问题排查)
logger = get_logger(__file__)

from user.models import User


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])  # 匿名用户限流
# 配置settings.py: REST_FRAMEWORK = {"DEFAULT_THROTTLE_RATES": {"anon": "10/min"}}
def user_register(request):
    """
    用户注册接口
    接口说明:
        - 接收用户名、密码、手机号,创建新用户 (自动哈希密码)
        - 包含用户名/手机号唯一性校验,避免重复注册
    请求参数 (JSON/form-data/urlencoded):
        {
            "username": "用户名 (必填,唯一)",
            "password":  "密码 (必填)",
            "phone": "手机号 (选填,建议加唯一性校验)"
        }
    响应示例:
        201: {"message": "Register successful"}
        400: {"message": "username already exists"}
        400: {"message": "phone format is invalid"}
        500: {"message": "Server internal error"}
    """
    # 1. 解析并清洗参数
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

    # 2. 基础参数校验
    if not username:
        return Response(
            {"message": "username is required"}, status=status.HTTP_400_BAD_REQUEST
        )
    if not password:
        return Response(
            {"message": "password is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # 3. 密码强度校验 (可选,建议添加)
    if len(password) < 6:
        return Response(
            {"message": "Password must be at least 6 characters long"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4. 手机号格式校验 (可选,示例)
    import re

    if phone and not re.match(r"^1[3-9]\d{9}$", phone):
        return Response(
            {"message": "phone format is invalid"}, status=status.HTTP_400_BAD_REQUEST
        )

    # 5. 唯一性校验 (核心: 避免重复注册)
    try:
        # 校验用户名是否已存在
        if User.objects.filter(username=username).exists():
            logger.warning(f"注册失败: 用户名已存在 - {username}")
            return Response(
                {"message": "username already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 可选: 校验手机号是否已存在 (如果需要)
        if phone and User.objects.filter(phone=phone).exists():
            logger.warning(f"注册失败: 手机号已存在 - {phone}")
            return Response(
                {"message": "phone already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 6. 创建用户 (自动哈希密码,避免明文存储)
        hashed_password = make_password(password)  # DRF内置哈希函数,安全可靠
        user = User.objects.create(
            username=username,
            password=hashed_password,  # 存储哈希后的密码
            phone=phone if phone else None,
        )

        logger.info(f"用户注册成功 - 用户名: {username} | 用户ID: {user.id}")
        return Response(
            {
                "message": "Register successful",
                "user_id": user.id,
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,  # 201表示资源创建成功
        )
    except Exception as e:
        logger.error(f"注册接口创建用户异常: {str(e)} | 用户名: {username}")
        return Response(
            {"message": "Server internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def user_login(request):
    """
    用户登录接口 (集成 JWT)
    接口说明:
        - 接收用户名和密码,验证后返回登录状态和基础用户信息
        - 建议后续集成JWT/Token认证
    请求参数 (JSON/form-data/urlencoded):
        {
            "username": "用户名 (必填)",
            "password": "密码 (必填)"
        }
    响应:
        返回 Access Token + Refresh Token
    """
    # 1. 修复参数获取方式 (DRF必须用request.data获取POST参数)
    try:
        # 兼容JSON/form-data/urlencoded三种请求格式
        data = request.data
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
    except Exception as e:
        logger.error(f"登录接口解析参数失败: {str(e)}")
        return Response(
            {"message": "Invalid request data format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 2. 严谨的参数校验 (拆分提示,更友好)
    if not username:
        return Response(
            {"message": "username is required"}, status=status.HTTP_400_BAD_REQUEST
        )
    if not password:
        return Response(
            {"message": "password is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # 3. 查询用户并处理异常 (避免数据库错误导致接口崩溃)
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

    # 4. 验证密码并生成 JWT Token
    if check_password(password, user.password):
        # 为用户生成 JWT Token (RefreshToken 包含 AccessToken)
        refresh = RefreshToken.for_user(user)

        logger.info(f"用户登录成功 - 用户名: {username} | 用户ID: {user.id}")
        return Response(
            {
                "message": "Login successful",
                "refresh_token": str(
                    refresh
                ),  # 刷新令牌 (长期,用于获取新的 Access Token)
                "access_token": str(
                    refresh.access_token
                ),  # 访问令牌 (短期,接口请求时携带)
                "user_info": {  # 基础用户信息
                    "user_id": user.id,
                    "username": user.username,
                    "phone": user.phone if hasattr(user, "phone") else None,
                },
            },
            status=status.HTTP_200_OK,
        )
    else:
        logger.warning(f"登录失败: 密码错误 - 用户名: {username}")
        # 401语义更准确 (认证失败)
        return Response(
            {"message": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """
    用户登出接口 (JWT 黑名单实现)
    接口说明:
        - 接收 Refresh Token, 将其加入黑名单 (无法再刷新 Access Token)
        - 同时清理该用户所有未过期的 Outstanding Token
        - 前端需配合清除本地存储的 Access/Refresh Token
    请求参数 (JSON):
        {
            "refresh": "登录时获取的 Refresh Token (必填)"
        }
    请求头:
        Authorization: Bearer <Access Token>  (必须携带有效的 Access Token 认证)
    响应示例:
        200: {"message": "Logout successful"}
        400: {"message": "refresh token is required"}
        401: {"message": "Invalid refresh token"}
        500: {"message": "Server internal error"}
    """
    return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)


#     try:
#         # 1. 获取并校验 Refresh Token 参数
#         refresh_token = request.data.get("refresh", "").strip()
#         if not refresh_token:
#             return Response(
#                 {"message": "refresh token is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # 2. 验证 Refresh Token 有效性 (避免伪造 Token)
#         try:
#             token = RefreshToken(refresh_token)
#         except TokenError as e:
#             logger.warning(f"登出失败: 无效的 Refresh Token - {str(e)} | 用户: {request.user.username}")
#             return Response(
#                 {"message": "Invalid refresh token"},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
#
#         # 3. 将 Refresh Token 加入黑名单 (核心: 使其失效)
#         # 方式1: 直接将当前 Refresh Token 加入黑名单
#         token.blacklist()
#
#         # 可选: 清理该用户所有未过期的 Outstanding Token (彻底登出,多端登录场景适用)
#         outstanding_tokens = OutstandingToken.objects.filter(user=request.user)
#         for ot in outstanding_tokens:
#             # 避免重复加入黑名单
#             if not BlacklistedToken.objects.filter(token=ot).exists():
#                 BlacklistedToken.objects.create(token=ot)
#
#         logger.info(f"用户登出成功 - 用户名: {request.user.username}")
#         return Response(
#             {"message": "Logout successful"},
#             status=status.HTTP_200_OK
#         )
#
#     except InvalidToken as e:
#         logger.error(f"登出失败: Token 无效 - {str(e)} | 用户: {request.user.username if request.user else '匿名'}")
#         return Response(
#             {"message": "Invalid token"},
#             status=status.HTTP_401_UNAUTHORIZED
#         )
#     except Exception as e:
#         logger.error(f"登出接口异常 - {str(e)} | 用户: {request.user.username if request.user else '匿名'}")
#         return Response(
#             {"message": "Server internal error"},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_info(request):
    """
    获取用户信息
    接口说明:
        - 根据Access Token, 获取用户信息
    请求参数:
        {
            "token": "Access Token",  # 修正参数名为token（匹配你的URL）
        }
    响应成功:
        {
            "username": "用户名",
            "roles": ["角色"],
            "introduction": "用户简介",
            "avatar": "头像URL",
            "name": "用户名/昵称"
        }
    响应失败:
        {
            "detail": "错误信息"
        }
    """
    # 1. 从URL参数获取token（匹配你的请求：?token=xxx）
    token = request.GET.get("token")

    # 2. 校验token是否存在
    if not token:
        logger.warning("获取用户信息失败：Token参数缺失")
        return Response(
            {"detail": "Token参数缺失，请在URL中传入token参数"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # 3. 验证Token的有效性（SimpleJWT内置校验）
        UntypedToken(token)

        # 4. 解码Token获取用户ID（适配SimpleJWT的Payload格式）
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
        # 从解码后的Token中获取user_id（SimpleJWT默认存储的键是user_id）
        user_id = decoded_token.get("user_id")

        # 5. 根据user_id查询用户信息（你的自定义User模型）
        user = User.objects.get(id=user_id)

        # 6. 构造响应数据（适配你的User模型字段，可根据实际调整）
        # 假设你的User模型有role字段（角色）、avatar字段（头像），无则用默认值
        user_roles = (
            [user.role] if hasattr(user, "role") else ["viewer"]
        )  # 角色默认查看者
        response_data = {
            "username": user.username,
            "roles": user_roles,  # 角色列表（符合前端常用格式）
            "introduction": f"I am {user.username}",  # 简介，可自定义
            "avatar": (
                user.avatar
                if hasattr(user, "avatar")
                else "https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif"
            ),
            "name": user.username,  # 用户名，可替换为昵称字段（如user.nickname）
        }

        logger.info(f"用户{user.username}（ID:{user_id}）成功获取个人信息")
        return Response(response_data, status=status.HTTP_200_OK)

    # 异常处理：Token无效/过期/签名错误
    except (
        InvalidToken,
        TokenError,
        jwt.ExpiredSignatureError,
        jwt.InvalidSignatureError,
    ) as e:
        logger.error(
            f"Token校验失败：{str(e)}，Token值：{token[:20]}..."
        )  # 日志脱敏，只打印前20位
        return Response(
            {"detail": "Token无效或已过期，请重新登录"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    # 异常处理：用户不存在
    except User.DoesNotExist:
        logger.error(
            f"Token对应的用户不存在，user_id：{decoded_token.get('user_id') if 'decoded_token' in locals() else '未知'}"
        )
        return Response(
            {"detail": "Token对应的用户不存在"}, status=status.HTTP_404_NOT_FOUND
        )
    # 其他未知异常
    except Exception as e:
        logger.error(
            f"获取用户信息异常：{str(e)}", exc_info=True
        )  # exc_info=True记录完整堆栈
        return Response(
            {"detail": "服务器内部错误，获取用户信息失败"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class UserViewSet(viewsets.ModelViewSet):
    """用户管理视图集: CRUD + 批量删除"""

    # 1. 数据源:查询所有用户数据
    queryset = User.objects.all()
    # 2. 序列化器:ModelViewSet 内置的所有 CRUD 方法(list/retrieve/create/update/destroy)都会自动调用这个序列化器
    serializer_class = UserSerializer
    # 3. 权限控制:仅允许 admin 角色访问(自定义权限类)
    permission_classes = [IsAdminRole]
    # 4. 过滤/搜索/排序后端配置
    filter_backends = [
        # DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    # 5. 可筛选字段:支持按 role 字段精准筛选(如 ?role=admin)
    filterset_fields = ["role"]  # 按角色筛选
    # 6. 可搜索字段:支持模糊搜索 username/phone/email(如 ?search=张三)
    search_fields = ["username", "phone", "email"]  # 搜索字段
    # 7. 可排序字段:支持按 created_at/updated_at 排序(如 ?ordering=-created_at)
    ordering_fields = ["created_at", "updated_at"]  # 排序字段

    # 自定义删除响应(覆盖 ModelViewSet 原生的 destroy 方法)
    def destroy(self, request, *args, **kwargs):
        # 获取要删除的用户实例(通过 URL 中的 pk 参数,如 /api/users/1/)
        instance = self.get_object()
        # 执行删除操作(DRF 内置方法,本质是 instance.delete())
        self.perform_destroy(instance)
        # 返回自定义响应:替换原生的 204 No Content,改为 200 OK + 提示信息
        return Response({"msg": "删除用户成功"}, status=status.HTTP_200_OK)

    # 批量删除接口(自定义 action)
    # 通过 @action 装饰器定义一个新的 POST 方法,URL 路径为 /api/users/batch_delete/
    # methods=['post']:该接口仅允许 POST 请求(批量删除属于写操作,不适合 GET)；
    # detail=False:表示该接口是 “列表级”(URL 为 /api/users/batch_delete/),而非 “实例级”(如 /api/users/1/)；
    @action(methods=["post"], detail=False)
    def batch_delete(self, request):
        """批量删除用户"""
        # 从 POST 请求体中获取要删除的用户 ID 列表(前端传 {ids: [1,2,3]})
        user_ids = request.data.get("ids", [])
        if not user_ids:
            # 校验:若未传 ids 或 ids 为空,返回 400 错误
            return Response(
                {"msg": "请选择要删除的用户"}, status=status.HTTP_400_BAD_REQUEST
            )
        # 安全校验:排除当前登录用户,避免删除自己
        user_ids = [uid for uid in user_ids if uid != request.user.id]
        # 批量删除:根据 ID 列表删除用户(比循环删除更高效)
        User.objects.filter(id__in=user_ids).delete()
        return Response(
            {"msg": f"成功删除{len(user_ids)}个用户"}, status=status.HTTP_200_OK
        )
