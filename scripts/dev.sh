#!/usr/bin/env bash
# 一键启动后端（自动创建虚拟环境、安装依赖、迁移、灌演示数据）
set -e
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "[1/3] 创建虚拟环境 .venv"
  python -m venv .venv
fi

# Windows(Git Bash) 与 macOS/Linux 的激活脚本路径不同
if [ -f .venv/Scripts/activate ]; then
  # shellcheck disable=SC1091
  source .venv/Scripts/activate
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "[2/3] 安装依赖"
python -m pip install -q -r requirements.txt

echo "[3/3] 启动服务"
exec python -m backend.dev "$@"
