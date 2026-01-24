from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import authenticate
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response   # DRF的Response类
from rest_framework import status              # DRF的状态码模块
import logging

from user.models import User


# Create your views here.
@api_view(["POST"])
def user_login(request):
    """
    user_login
    """
    user_name = request.get("user_name")
    hashed_password = request.get("hashed_password")
    if not user_name or not hashed_password:
        return Response({"message": "user_name,password are required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(user_name=user_name)
    except User.DoesNotExist:
        return Response({"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)

    # Verify password
    if user and check_password(hashed_password, user.password):
        return Response({"message": "Login successful"}, status=status.HTTP_200_OK)
    else:
        return Response({"message": ""}, status=status.HTTP_404_NOT_FOUND)
