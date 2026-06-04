"""
本地模型快速测试脚本
用于验证本地模型是否正常工作
"""

import os
import json
from langchain_openai import ChatOpenAI

def test_local_model():
    """测试本地模型连接"""
    print("=" * 60)
    print("本地模型测试")
    print("=" * 60)

    # 读取环境变量
    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY", "ollama")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", "http://localhost:11434/v1")

    print(f"\n配置信息：")
    print(f"  API Key: {api_key}")
    print(f"  Base URL: {base_url}")

    # 读取模型配置
    config_path = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "."), "config/agent_llm_config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        model_name = config['config'].get('model', 'qwen2.5:7b')

    print(f"  模型名称: {model_name}")

    try:
        # 创建 LLM 客户端
        print(f"\n正在连接本地模型...")
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
            timeout=60
        )

        # 测试简单对话
        print(f"\n测试 1：简单对话...")
        response = llm.invoke("你好，请用一句话介绍你自己。")
        print(f"  ✅ 成功")
        print(f"  回复: {response.content}")

        # 测试复杂推理
        print(f"\n测试 2：复杂推理...")
        prompt = "请分析：1+2+3+4+5等于多少？请给出计算过程。"
        response = llm.invoke(prompt)
        print(f"  ✅ 成功")
        print(f"  回复: {response.content}")

        # 测试 JSON 输出
        print(f"\n测试 3：JSON 输出...")
        prompt = "请用 JSON 格式输出今天的天气预测，包含 temperature 和 condition 字段。"
        response = llm.invoke(prompt)
        print(f"  ✅ 成功")
        print(f"  回复: {response.content}")

        print(f"\n" + "=" * 60)
        print("🎉 所有测试通过！本地模型工作正常。")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 测试失败")
        print(f"错误信息: {str(e)}")
        print(f"\n排查建议：")
        print(f"  1. 检查 Ollama 服务是否启动：运行 'ollama list'")
        print(f"  2. 检查模型是否安装：运行 'ollama pull {model_name}'")
        print(f"  3. 检查 API 服务：访问 http://localhost:11434/api/tags")
        print(f"  4. 检查配置文件：确认 .env 和 agent_llm_config.json 配置正确")
        return False


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 添加项目路径到 sys.path
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", str(Path(__file__).parent.parent))
    if workspace_path not in sys.path:
        sys.path.insert(0, workspace_path)

    success = test_local_model()
    sys.exit(0 if success else 1)
