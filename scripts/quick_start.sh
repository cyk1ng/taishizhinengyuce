#!/bin/bash
# 配网调度智能预测系统 - 快速启动脚本

echo "======================================"
echo "  配网调度业务量智能预测系统"
echo "======================================"
echo ""

# 步骤1：解压文件（如果存在tar.gz文件）
if [ -f project_*.tar.gz ]; then
    echo "📦 正在解压项目文件..."
    tar -xzf project_*.tar.gz
    echo "✅ 解压完成"
    cd project_*/
fi

# 步骤2：检查Python版本
echo ""
echo "🔍 检查Python版本..."
python_version=$(python3 --version 2>&1)
if [[ $? -eq 0 ]]; then
    echo "✅ $python_version"
else
    echo "❌ 未检测到Python，请先安装Python 3.10+"
    exit 1
fi

# 步骤3：安装依赖
echo ""
echo "📦 安装依赖包..."
pip install -r requirements.txt -q
if [[ $? -eq 0 ]]; then
    echo "✅ 依赖安装完成"
else
    echo "⚠️  依赖安装可能有问题，继续尝试..."
fi

# 步骤4：检查配置文件
echo ""
echo "🔍 检查配置文件..."
if [ -f "config/agent_llm_config.json" ]; then
    echo "✅ 配置文件存在"
else
    echo "⚠️  配置文件缺失，请检查"
fi

# 步骤5：启动提示
echo ""
echo "======================================"
echo "  准备就绪！"
echo "======================================"
echo ""
echo "📋 接下来请执行："
echo ""
echo "1️⃣  配置环境变量（必需）："
echo "   export COZE_WORKLOAD_IDENTITY_API_KEY='your_api_key'"
echo "   export COZE_INTEGRATION_MODEL_BASE_URL='https://api.coze.cn'"
echo ""
echo "2️⃣  运行智能体："
echo "   python src/main.py"
echo ""
echo "或者使用测试命令："
echo "   python -c \"from agents.agent import build_agent; print('✅ 就绪')\""
echo ""
