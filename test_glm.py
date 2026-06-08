"""
GLM-4-Flash API 测试脚本
直接调用智谱API，查看详细错误信息
"""
import os
import json
import httpx
from pathlib import Path

# 加载 .env
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载 .env: {env_path}")

api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")

# 打印配置
masked_key = api_key[:8] + "..." + api_key[-4:] if api_key and len(api_key) > 12 else "未设置"
print(f"🔑 API Key: {masked_key}")
print(f"🌐 Base URL: {base_url}")

if not api_key:
    print("❌ 未设置 COZE_WORKLOAD_IDENTITY_API_KEY")
    exit(1)

# 测试1: 最简单的对话（无工具）
print("\n" + "="*60)
print("📝 测试1: 最简单的对话（无tools）")
print("="*60)

url = base_url.rstrip("/") + "/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "glm-4-flash",
    "messages": [
        {"role": "user", "content": "你好"}
    ],
    "stream": False,
    "temperature": 0.7,
    "max_tokens": 100
}

try:
    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ 成功! 回复: {result['choices'][0]['message']['content']}")
    else:
        print(f"❌ 失败! 响应体: {resp.text[:1000]}")
except Exception as e:
    print(f"❌ 异常: {type(e).__name__}: {e}")

# 测试2: 带tools的对话
print("\n" + "="*60)
print("📝 测试2: 带tools的对话")
print("="*60)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

payload2 = {
    "model": "glm-4-flash",
    "messages": [
        {"role": "system", "content": "你是一个天气助手，请使用工具回答用户问题。"},
        {"role": "user", "content": "北京今天天气怎么样？"}
    ],
    "tools": tools,
    "tool_choice": "auto",
    "stream": False,
    "temperature": 0.7,
    "max_tokens": 1000
}

try:
    resp2 = httpx.post(url, headers=headers, json=payload2, timeout=30)
    print(f"状态码: {resp2.status_code}")
    if resp2.status_code == 200:
        result2 = resp2.json()
        msg = result2['choices'][0]['message']
        print(f"✅ 成功!")
        print(f"  回复: {msg.get('content', '')}")
        if msg.get('tool_calls'):
            print(f"  工具调用: {json.dumps(msg['tool_calls'], ensure_ascii=False, indent=2)}")
    else:
        print(f"❌ 失败! 响应体: {resp2.text[:2000]}")
except Exception as e:
    print(f"❌ 异常: {type(e).__name__}: {e}")

print("\n" + "="*60)
print("测试完成")