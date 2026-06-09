"""分步测试 ChatOpenAI 调用 GLM-4-Flash"""
import os, json
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")

# 测试1: ChatOpenAI 最简调用（不传tools）
print("=== 测试1: ChatOpenAI 最简 ===")
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model="glm-4-flash",
    api_key=api_key,
    base_url=base_url,
    temperature=0.7,
    max_tokens=100,
    streaming=False,
    timeout=30,
)
try:
    from langchain_core.messages import HumanMessage
    r = llm.invoke([HumanMessage(content="你好")])
    print(f"✅ 成功: {r.content[:50]}")
except Exception as e:
    print(f"❌ {e}")

# 测试2: ChatOpenAI + 1个tool
print("\n=== 测试2: ChatOpenAI + 1个tool ===")
llm2 = ChatOpenAI(
    model="glm-4-flash",
    api_key=api_key,
    base_url=base_url,
    temperature=0.7,
    max_tokens=1000,
    streaming=False,
    timeout=30,
)
from langchain_core.tools import tool
@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气"""
    return f"{city}天气晴朗"
try:
    r2 = llm2.bind_tools([get_weather]).invoke([HumanMessage(content="北京天气如何？")])
    print(f"✅ 成功, tool_calls: {r2.tool_calls}")
except Exception as e:
    print(f"❌ {e}")

# 测试3: 用系统提示词 + tools
print("\n=== 测试3: system + tools ===")
llm3 = ChatOpenAI(
    model="glm-4-flash",
    api_key=api_key,
    base_url=base_url,
    temperature=0.7,
    max_tokens=1000,
    streaming=False,
    timeout=30,
)
from langchain_core.messages import SystemMessage
try:
    r3 = llm3.bind_tools([get_weather]).invoke([
        SystemMessage(content="你是配网调度助手"),
        HumanMessage(content="北京天气")
    ])
    print(f"✅ 成功, tool_calls: {r3.tool_calls}")
except Exception as e:
    print(f"❌ {e}")