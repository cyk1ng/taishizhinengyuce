#!/bin/bash

echo "========================================"
echo "  连接本地Ollama - 快速启动脚本"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到Python，请先安装Python"
    exit 1
fi

echo "✅ 检测到Python"
echo ""

# 检查Ollama是否安装
if ! command -v ollama &> /dev/null; then
    echo "❌ 未检测到Ollama，请先安装Ollama"
    echo "   macOS: brew install ollama"
    echo "   Linux: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

echo "✅ 检测到Ollama"
echo ""

# 检查Ollama服务是否运行
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama服务未运行，正在启动..."
    echo ""
    echo "请在新终端运行以下命令启动Ollama服务："
    echo "   ollama serve"
    echo ""
    read -p "等待Ollama启动后，按Enter键继续..."
fi

echo "✅ Ollama服务正在运行"
echo ""

# 检查模型是否已下载
echo "检查qwen2.5:7b模型..."
if ! curl -s http://localhost:11434/api/tags | grep -q "qwen2.5:7b"; then
    echo "❌ 模型qwen2.5:7b未安装"
    echo ""
    echo "正在下载模型..."
    echo "   ollama pull qwen2.5:7b"
    echo ""
    if ! ollama pull qwen2.5:7b; then
        echo "❌ 模型下载失败"
        exit 1
    fi
fi

echo "✅ 模型qwen2.5:7b已安装"
echo ""

# 运行测试脚本
echo "运行连接测试..."
echo ""
if ! python3 scripts/test_ollama_connection.py; then
    echo ""
    echo "❌ 连接测试失败"
    echo ""
    echo "请检查："
    echo "  1. Ollama服务是否正常运行"
    echo "  2. 模型是否已下载"
    echo "  3. 项目配置是否正确"
    exit 1
fi

echo ""
echo "========================================"
echo "  ✅ 连接测试通过！"
echo "========================================"
echo ""
echo "🚀 启动项目："
echo ""
echo "1. 确保Ollama服务正在运行（已确认）"
echo ""
echo "2. 启动后端服务（新开一个终端）："
echo "   cd $(pwd)"
echo "   python3 src/main.py"
echo ""
echo "3. 启动前端服务（新开一个终端）："
echo "   cd $(pwd)"
echo "   python3 -m http.server 8000 --directory frontend"
echo ""
echo "4. 访问界面："
echo "   http://localhost:8000"
echo ""
echo "📚 查看文档："
echo "   连接本地Ollama指南.md"
echo ""
