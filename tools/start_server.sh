#!/bin/zsh

# ===================== 基础配置 =====================
SCRIPT_DIR=$(cd "$(dirname "${0}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/../" && pwd)
# 虚拟环境目录
VENV_PARENT_DIR=$(cd "${PROJECT_ROOT}/../" && pwd)
VENV_DIR="${VENV_PARENT_DIR}/myvenv"
# 依赖文件路径
REQUIREMENTS_FILE=${PROJECT_ROOT}/requirements.txt
# 服务启动地址和端口
RUN_HOST="127.0.0.1"
RUN_PORT="5000"

# ===================== 验证基础依赖 =====================
# 检查python3是否可用
if ! command -v python3 &> /dev/null; then
    echo "未找到python3, 请先安装Python 3.8+"
    exit 0
fi

# 检查requirements.txt是否存在
if [ ! -f "${REQUIREMENTS_FILE}" ]; then
    echo "依赖文件不存在：${REQUIREMENTS_FILE}"
fi

# ===================== 创建虚拟环境（若不存在） ================
if [ ! -d "${VENV_DIR}" ]; then
    echo "🔧 虚拟环境目录不存在，正在创建：${VENV_DIR}"
    # 创建虚拟环境（禁用pip升级提示，减少干扰）
    python3 -m venv "${VENV_DIR}" || echo "虚拟环境创建失败"
    echo "✅ 虚拟环境创建成功"
else
    echo "ℹ️  虚拟环境已存在：${VENV_DIR}"
fi

# ===================== 激活虚拟环境并验证 =====================
echo "🔧 正在激活虚拟环境..."
# 激活虚拟环境（zsh兼容写法）
source "${VENV_DIR}/bin/activate" || echo "虚拟环境激活失败"
echo "👓 VIRTUAL_ENV=${VIRTUAL_ENV}"

# 验证虚拟环境是否激活成功（检查python路径是否指向虚拟环境）
if [[ ! "${VIRTUAL_ENV}" == "${VENV_DIR}" ]]; then
    echo "虚拟环境激活异常, VIRTUAL_ENV变量不匹配"
fi
echo "✅ 虚拟环境激活成功(当前Python:$(which python))"

# ===================== 安装依赖 =====================
echo "🔧 正在安装依赖：${REQUIREMENTS_FILE}"
# 升级pip并安装依赖（--upgrade pip 避免旧pip安装失败）
python3 -m pip install --upgrade pip -q || echo "pip升级失败"
python3 -m pip install -r "${REQUIREMENTS_FILE}" -q || echo "依赖安装失败"
echo "✅ 依赖安装完成"

# ===================== 启动服务 =====================
echo "🚀 正在启动服务: http://${RUN_HOST}:${RUN_PORT}"
python3 $PROJECT_ROOT/manage.py runserver "${RUN_HOST}:${RUN_PORT}"
