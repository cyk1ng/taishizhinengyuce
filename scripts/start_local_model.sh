#!/bin/bash

# ============================================================
# 本地模型一键启动脚本（Linux/macOS）
# ============================================================

echo ""
echo "============================================================"
echo "       配网调度系统 - 本地模型启动脚本"
echo "============================================================"
echo ""

# 检查 Ollama 是否安装
echo "[1/4] 检查 Ollama 是否安装..."
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama 未安装！"
    echo "请访问 https://ollama.com/download 下载安装"
    exit 1
fi
echo "✅ Ollama 已安装"

# 检查模型是否已下载
echo ""
echo "[2/4] 检查本地模型..."
if ! ollama list | grep -q "qwen2.5:7b"; then
    echo "⚠️  qwen2.5:7b 模型未安装，正在下载..."
    ollama pull qwen2.5:7b
    if [ $? -ne 0 ]; then
        echo "❌ 模型下载失败！"
        exit 1
    fi
fi
echo "✅ qwen2.5:7b 模型已就绪"

# 检查 Ollama 服务是否已在运行
echo ""
echo "[3/4] 启动 Ollama 服务..."
if curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "✅ Ollama 服务已在运行"
else
    echo "正在启动 Ollama 服务..."
    ollama serve &
    OLLAMA_PID=$!
    sleep 3

    # 验证服务是否启动成功
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo "❌ Ollama 服务启动失败！"
        echo "请检查端口 11434 是否被占用"
        exit 1
    fi
    echo "✅ Ollama 服务已启动 (PID: $OLLAMA_PID)"
fi

# 测试本地模型
echo ""
echo "[4/4] 测试本地模型连接..."
python scripts/test_local_model.py
if [ $? -ne 0 ]; then
    echo "⚠️  模型测试失败，请检查配置"
else
    echo "✅ 本地模型测试通过"
fi

echo ""
echo "============================================================"
echo "🎉 本地模型启动成功！"
echo "============================================================"
echo ""
echo "服务信息："
echo "  - Ollama API: http://localhost:11434"
echo "  - 模型名称: qwen2.5:7b"
echo "  - 查看模型: ollama list"
echo ""
echo "下一步："
echo "  1. 启动系统: python src/main.py"
echo "  2. 访问界面: http://localhost:8000"
echo ""
echo "常用命令："
echo "  - 查看模型: ollama list"
echo "  - 测试模型: ollama run qwen2.5:7b \"你好\""
echo "  - 停止服务: kill $OLLAMA_PID"
echo ""
