"""
配网调度业务量智能预测Agent

核心功能：
1. 多源数据融合：整合历史调度、天气、节假日、设备状态等数据
2. 业务量预测：基于AI预测未来调度业务量趋势
3. 人员决策支持：生成科学的值班人员调整建议
4. 风险预警：识别异常和潜在风险，提供预警建议

架构特点：
- 模块化设计：各功能模块独立、可替换
- 标准化接口：便于本地化部署和集成
- 配置驱动：通过配置文件灵活调整参数
"""

import os
import json
from typing import Annotated
from pathlib import Path
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    # 从项目根目录加载 .env
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量文件: {env_path}")
except ImportError:
    print("⚠️  未安装 python-dotenv，跳过 .env 文件加载")
    print("   提示：运行 'pip install python-dotenv' 可启用此功能")

# 导入工具模块
from tools.data_fusion import (
    get_historical_dispatch_data,
    get_weather_forecast,
    get_holiday_info,
    get_equipment_status,
    fuse_multi_source_data
)
from tools.prediction import (
    predict_dispatch_volume,
    analyze_prediction_trend
)
from tools.decision import (
    generate_staffing_decision,
    optimize_shift_schedule,
    generate_decision_report
)
# 导入排班工具模块
from tools.scheduling import (
    get_schedule_staff_info,
    get_existing_schedule,
    generate_intelligent_schedule,
    analyze_schedule_fairness,
    export_schedule_report,
    save_schedule_records
)


# 配置文件路径
LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近20轮对话（40条消息）
MAX_MESSAGES = 40


def _windowed_messages(old, new):
    """滑动窗口：只保留最近MAX_MESSAGES条消息"""
    combined = add_messages(old, new)
    # 确保返回的是消息列表，而不是BaseMessage对象
    if hasattr(combined, '__iter__'):
        return list(combined)[-MAX_MESSAGES:]
    return combined


class AgentState(MessagesState):
    """Agent状态定义"""
    messages: Annotated[list[AnyMessage], _windowed_messages]


def build_agent(ctx=None):
    """
    构建配网调度业务量智能预测Agent
    
    参数：
    - ctx: 运行时上下文（用于请求追踪）
    
    返回：
    - Agent实例
    """
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)
    
    # 加载配置
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    
    # 获取认证信息
    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")
    
    # 环境变量检查
    if not api_key:
        raise ValueError(
            "❌ 缺少必要的环境变量: COZE_WORKLOAD_IDENTITY_API_KEY\n\n"
            "解决方法：\n"
            "1. 在项目根目录创建 .env 文件\n"
            "2. 添加以下内容：\n"
            "   COZE_WORKLOAD_IDENTITY_API_KEY=your_api_key_here\n"
            "   COZE_INTEGRATION_MODEL_BASE_URL=https://api.coze.cn/v1\n"
            "3. 或在 Coze 云端环境中运行（会自动注入环境变量）\n\n"
            "详细配置请参考 .env.example 文件"
        )
    
    if not base_url:
        base_url = "https://api.coze.cn/v1"  # 默认使用 Coze API
        print(f"⚠️  未设置 COZE_INTEGRATION_MODEL_BASE_URL，使用默认值: {base_url}")
    
    # 初始化LLM
    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.3),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )
    
    # 注册工具
    tools = [
        # 数据融合工具
        get_historical_dispatch_data,
        get_weather_forecast,
        get_holiday_info,
        get_equipment_status,
        fuse_multi_source_data,
        
        # 预测工具
        predict_dispatch_volume,
        analyze_prediction_trend,
        
        # 决策工具
        generate_staffing_decision,
        optimize_shift_schedule,
        generate_decision_report,
        
        # 排班工具
        get_schedule_staff_info,
        get_existing_schedule,
        generate_intelligent_schedule,
        analyze_schedule_fairness,
        export_schedule_report,
        save_schedule_records
    ]
    
    # 创建Agent
    agent = create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=tools,
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
    
    return agent


# Agent元数据
AGENT_METADATA = {
    "name": "配网调度业务量智能预测Agent",
    "version": "1.1.0",
    "description": "基于多源数据融合和AI技术的配网调度业务量预测、人员决策支持与智能排班系统",
    "capabilities": [
        "多源数据融合",
        "业务量智能预测",
        "人员配置决策",
        "风险预警分析",
        "智能排班生成",
        "排班公平性分析",
        "排班方案优化"
    ],
    "data_sources": [
        "历史调度记录",
        "天气预报",
        "节假日日历",
        "设备状态监控",
        "人员信息表(working_user)",
        "班组表(working_groups)",
        "排班记录表(work_schedule_recode)"
    ],
    "output_formats": [
        "JSON格式预测结果",
        "Markdown格式决策报告",
        "人员调整建议",
        "智能排班方案",
        "排班公平性报告"
    ],
    "deployment_requirements": {
        "python_version": ">=3.10",
        "dependencies": [
            "langchain",
            "langgraph",
            "coze-coding-dev-sdk",
            "psycopg2-binary"
        ],
        "environment_variables": [
            "COZE_WORKLOAD_IDENTITY_API_KEY",
            "COZE_INTEGRATION_MODEL_BASE_URL",
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "WEATHER_API_ENDPOINT",
            "WEATHER_API_KEY",
            "EQUIPMENT_API_ENDPOINT"
        ],
        "config_files": [
            "config/agent_llm_config.json",
            "config/data_sources.json",
            "config/prediction_config.json",
            "config/decision_config.json"
        ]
    }
}
