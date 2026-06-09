"""
最终测试：验证 agent.py 使用 create_agent（新API）+ GLM-4-Flash 能否正常工作
"""
import os
import sys
from pathlib import Path

# 设置环境变量
os.environ.setdefault('COZE_WORKLOAD_IDENTITY_API_KEY', '9bb00e61be824857808f2ac60b21e159.0aU5VQzzgljrnKfP')
os.environ.setdefault('COZE_INTEGRATION_MODEL_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4/')
os.environ.setdefault('COZE_WORKSPACE_PATH', '/workspace/projects')

# 添加 src 到 path
sys.path.insert(0, '/workspace/projects/src')

# 直接从 agent 模块导入 build_agent
from agents.agent import build_agent

print("=" * 60)
print("🔧 构建Agent...")
agent = build_agent()
print("✅ Agent构建成功!")
print(f"  类型: {type(agent).__name__}")

print("\n" + "=" * 60)
print("🔧 测试Agent调用...")

# 准备输入
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "test_thread_001"}}

# 调用 agent
result = agent.invoke(
    {"messages": [HumanMessage(content="你好，请介绍一下你自己和你的能力")]},
    config=config
)

# 检查结果
messages = result.get("messages", [])
last_msg = messages[-1] if messages else None
if last_msg:
    print(f"\n✅ Agent回复成功!")
    print(f"   内容: {last_msg.content[:200]}...")
else:
    print("\n❌ 未收到回复")

print("\n" + "=" * 60)
print("测试完成!")