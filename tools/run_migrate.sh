#!/bin/zsh

# ===================== 基础配置 =====================
SCRIPT_DIR=$(cd "$(dirname "${0}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/../" && pwd)
# 虚拟环境目录
VENV_PARENT_DIR=$(cd "${PROJECT_ROOT}/../" && pwd)
VENV_DIR="${VENV_PARENT_DIR}/myvenv"

# 生成迁移文件（migrations）
${VENV_DIR}/bin/python3 ${PROJECT_ROOT}/manage.py makemigrations
# 将migrations文件夹中的改动同步到数据库
${VENV_DIR}/bin/python3 ${PROJECT_ROOT}/manage.py migrate
