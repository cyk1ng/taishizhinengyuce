#!/bin/bash

echo "========================================"
echo "配网调度业务量智能预测系统"
echo "========================================"
echo ""

# 设置工作空间路径
export COZE_WORKSPACE_PATH="$(cd "$(dirname "$0")" && pwd)"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "[警告] 未找到 .env 文件"
    echo "请复制 .env.example 为 .env 并填写配置"
    echo ""
fi

# 启动服务
echo "[启动] 正在启动服务..."
echo "[地址] http://127.0.0.1:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

python src/main.py
