from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,  # 刷新 Access Token
    TokenVerifyView    # 验证 Token 是否有效
)
from .views import user_login, user_register

urlpatterns = [
    # 登录（获取 Token）
    path('login/', user_login, name='user_login'),
    # 注册
    path('register/', user_register, name='user_register'),
    # JWT 辅助接口：刷新 Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # JWT 辅助接口：验证 Token
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
