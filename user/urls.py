from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,  # 刷新 Access Token
    TokenVerifyView    # 验证 Token 是否有效
)
from .views import user_register, user_login, user_logout, get_user_info

urlpatterns = [
    # 注册
    path('register/', user_register, name='user_register'),
    # 登录（获取 Token）
    path('login/', user_login, name='user_login'),
    # 退出（携带 Token）
    path('logout/', user_logout, name='user_logout'),
    # 获取用户信息（携带 Token）
    path('get_user_info/', get_user_info, name='get_user_info'),
    # JWT 辅助接口：刷新 Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # JWT 辅助接口：验证 Token
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
