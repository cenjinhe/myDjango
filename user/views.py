from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework_simplejwt.tokens import RefreshToken    # 导入 JWT Token 生成模块
from rest_framework.throttling import AnonRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging

# 配置日志（方便线上问题排查）
logger = logging.getLogger(__name__)

from user.models import User


@api_view(["POST"])
@permission_classes([AllowAny])        # 登录接口允许匿名访问
def user_login(request):
    """
    用户登录接口（集成 JWT）
    接口说明：
        - 接收用户名和密码，验证后返回登录状态和基础用户信息
        - 建议后续集成JWT/Token认证
    请求参数（JSON/form-data/urlencoded）：
        {
            "user_name": "用户名（必填）",
            "password": "密码（必填）"
        }
    响应：
        返回 Access Token + Refresh Token
    """
    # 1. 修复参数获取方式（DRF必须用request.data获取POST参数）
    try:
        # 兼容JSON/form-data/urlencoded三种请求格式
        data = request.data
        user_name = data.get("user_name", "").strip()  # 去除首尾空格
        password = data.get("password", "").strip()    # 变量名修正：原hashed_password易混淆（实际是明文）
    except Exception as e:
        logger.error(f"登录接口解析参数失败: {str(e)}")
        return Response({"message": "Invalid request data format"}, status=status.HTTP_400_BAD_REQUEST)

    # 2. 严谨的参数校验（拆分提示，更友好）
    if not user_name:
        return Response({"message": "user_name is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not password:
        return Response({"message": "password is required"}, status=status.HTTP_400_BAD_REQUEST)

    # 3. 查询用户并处理异常（避免数据库错误导致接口崩溃）
    try:
        user = User.objects.get(user_name=user_name)
    except User.DoesNotExist:
        logger.warning(f"登录失败：用户不存在 - 用户名：{user_name}")
        return Response({"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"登录接口查询用户异常: {str(e)} | 用户名：{user_name}")
        return Response({"message": "Server internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 4. 验证密码并生成 JWT Token
    if check_password(password, user.password):
        # 为用户生成 JWT Token（RefreshToken 包含 AccessToken）
        refresh = RefreshToken.for_user(user)

        logger.info(f"用户登录成功 - 用户名：{user_name} | 用户ID：{user.id}")
        return Response(
            {
                "message": "Login successful",
                "refresh": str(refresh),                # 刷新令牌（长期，用于获取新的 Access Token）
                "access": str(refresh.access_token),    # 访问令牌（短期，接口请求时携带）
                "user_info": {                          # 基础用户信息
                    "user_id": user.id,
                    "user_name": user.user_name,
                    "phone": user.phone if hasattr(user, 'phone') else None
                }
            },
            status=status.HTTP_200_OK
        )
    else:
        logger.warning(f"登录失败：密码错误 - 用户名：{user_name}")
        # 401语义更准确（认证失败）
        return Response({"message": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
@permission_classes([AllowAny])        # 登录接口允许匿名访问
@throttle_classes([AnonRateThrottle])  # 匿名用户限流
# 配置settings.py：REST_FRAMEWORK = {"DEFAULT_THROTTLE_RATES": {"anon": "10/min"}}
def user_register(request):
    """
    用户注册接口
    接口说明：
        - 接收用户名、密码、手机号，创建新用户（自动哈希密码）
        - 包含用户名/手机号唯一性校验，避免重复注册
    请求参数（JSON/form-data/urlencoded）：
        {
            "user_name": "用户名（必填，唯一）",
            "password":  "密码（必填）",
            "phone": "手机号（选填，建议加唯一性校验）"
        }
    响应示例：
        201: {"message": "Register successful", "user_id": 1, "user_name": "test"}
        400: {"message": "user_name already exists"}
        400: {"message": "phone format is invalid"}
        500: {"message": "Server internal error"}
    """
    # 1. 解析并清洗参数
    try:
        data = request.data
        username = data.get("user_name", "").strip()
        password = data.get("hashed_password", "").strip()
        phone = data.get("phone", "").strip()
    except Exception as e:
        logger.error(f"注册接口解析参数失败: {str(e)}")
        return Response({"message": "Invalid request data format"}, status=status.HTTP_400_BAD_REQUEST)

    # 2. 基础参数校验
    if not username:
        return Response({"message": "username is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not password:
        return Response({"message": "password is required"}, status=status.HTTP_400_BAD_REQUEST)

    # 3. 密码强度校验（可选，建议添加）
    if len(password) < 6:
        return Response({"message": "Password must be at least 6 characters long"}, status=status.HTTP_400_BAD_REQUEST)

    # 4. 手机号格式校验（可选，示例）
    import re
    if phone and not re.match(r'^1[3-9]\d{9}$', phone):
        return Response({"message": "phone format is invalid"}, status=status.HTTP_400_BAD_REQUEST)

    # 5. 唯一性校验（核心：避免重复注册）
    try:
        # 校验用户名是否已存在
        if User.objects.filter(username=username).exists():
            logger.warning(f"注册失败：用户名已存在 - {username}")
            return Response(
                {"message": "username already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 可选：校验手机号是否已存在（如果需要）
        if phone and User.objects.filter(phone=phone).exists():
            logger.warning(f"注册失败：手机号已存在 - {phone}")
            return Response(
                {"message": "phone already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 6. 创建用户（自动哈希密码，避免明文存储）
        hashed_password = make_password(password)  # DRF内置哈希函数，安全可靠
        user = User.objects.create(
            username=username,
            password=hashed_password,  # 存储哈希后的密码
            phone=phone if phone else ""
        )

        logger.info(f"用户注册成功 - 用户名：{username} | 用户ID：{user.id}")
        return Response(
            {
                "message": "Register successful",
                "user_id": user.id,
                "username": user.username
            },
            status=status.HTTP_201_CREATED  # 201表示资源创建成功
        )
    except Exception as e:
        logger.error(f"注册接口创建用户异常: {str(e)} | 用户名：{username}")
        return Response(
            {"message": "Server internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

#
# @api_view(["POST"])
# @permission_classes([IsAuthenticated])  # 登出接口需要先认证（必须携带有效的 Access Token）
# def user_logout(request):
#     """
#     用户登出接口（JWT 黑名单实现）
#     接口说明：
#         - 接收 Refresh Token，将其加入黑名单（无法再刷新 Access Token）
#         - 同时清理该用户所有未过期的 Outstanding Token
#         - 前端需配合清除本地存储的 Access/Refresh Token
#     请求参数（JSON）：
#         {
#             "refresh": "登录时获取的 Refresh Token（必填）"
#         }
#     请求头：
#         Authorization: Bearer <Access Token> （必须携带有效的 Access Token 认证）
#     响应示例：
#         200: {"message": "Logout successful"}
#         400: {"message": "refresh token is required"}
#         401: {"message": "Invalid refresh token"}
#         500: {"message": "Server internal error"}
#     """
#     try:
#         # 1. 获取并校验 Refresh Token 参数
#         refresh_token = request.data.get("refresh", "").strip()
#         if not refresh_token:
#             return Response(
#                 {"message": "refresh token is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # 2. 验证 Refresh Token 有效性（避免伪造 Token）
#         try:
#             token = RefreshToken(refresh_token)
#         except TokenError as e:
#             logger.warning(f"登出失败：无效的 Refresh Token - {str(e)} | 用户：{request.user.user_name}")
#             return Response(
#                 {"message": "Invalid refresh token"},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
#
#         # 3. 将 Refresh Token 加入黑名单（核心：使其失效）
#         # 方式1：直接将当前 Refresh Token 加入黑名单
#         token.blacklist()
#
#         # 可选：清理该用户所有未过期的 Outstanding Token（彻底登出，多端登录场景适用）
#         outstanding_tokens = OutstandingToken.objects.filter(user=request.user)
#         for ot in outstanding_tokens:
#             # 避免重复加入黑名单
#             if not BlacklistedToken.objects.filter(token=ot).exists():
#                 BlacklistedToken.objects.create(token=ot)
#
#         logger.info(f"用户登出成功 - 用户名：{request.user.user_name}")
#         return Response(
#             {"message": "Logout successful"},
#             status=status.HTTP_200_OK
#         )
#
#     except InvalidToken as e:
#         logger.error(f"登出失败：Token 无效 - {str(e)} | 用户：{request.user.user_name if request.user else '匿名'}")
#         return Response(
#             {"message": "Invalid token"},
#             status=status.HTTP_401_UNAUTHORIZED
#         )
#     except Exception as e:
#         logger.error(f"登出接口异常 - {str(e)} | 用户：{request.user.user_name if request.user else '匿名'}")
#         return Response(
#             {"message": "Server internal error"},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )
