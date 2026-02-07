from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,  # 刷新 Access Token
    TokenVerifyView    # 验证 Token 是否有效
)
from . import views

# 1. 注册视图集（用户管理）：DRF 路由器自动生成 CRUD 路由
router = DefaultRouter()
# 注册 UserViewSet，前缀为 'users'，会生成 /users/、/users/{id}/、/users/batch_delete/ 等路由
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    # 注册
    path('register/', views.user_register, name='user_register'),
    # 登录（获取 Token）
    path('login/', views.user_login, name='user_login'),
    # 退出（携带 Token）
    path('logout/', views.user_logout, name='user_logout'),
    # 获取用户信息（携带 Token）
    path('get_user_info/', views.get_user_info, name='get_user_info'),
    # JWT 辅助接口：刷新 Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # JWT 辅助接口：验证 Token
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # 把视图集路由挂载到当前 urlpatterns 中
    path('', include(router.urls)),
]
