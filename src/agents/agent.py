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
import re
from typing import Annotated
from pathlib import Path
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, AIMessage, ToolMessage

from storage.memory.memory_saver import get_memory_saver
import importlib

# 尝试加载 .env 文件
try:
    _dotenv = importlib.import_module('dotenv')
    load_dotenv = _dotenv.load_dotenv
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
from tools.time_series_prediction import (
    predict_with_time_series,
    evaluate_prediction_performance
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
# 导入工作量统计工具模块
from tools.workload_statistics import (
    get_realtime_workload_dashboard,
    get_workload_weights_config,
    analyze_staff_requirement,
    get_workload_by_module
)
# 导入人员需求预测工具模块
from tools.staff_prediction import (
    predict_staffing_need,
    generate_staffing_recommendations,
    evaluate_staff_efficiency,
    calculate_optimal_staffing
)
# 导入态势感知工具模块
from tools.situation_awareness import (
    assess_situation_awareness,
    generate_situation_report,
    get_situation_dashboard
)
# 导入风险预警工具模块
from tools.risk_alert import (
    assess_comprehensive_risk,
    generate_risk_alert_report,
    check_daily_risks
)
# 导入计划工作量统计工具模块（更新：包含计划工作量和非计划工作量）
from tools.plan_workload import (
    calculate_plan_workload,
    calculate_non_plan_workload,
    get_workload_dashboard,
    manual_adjust_plan_workload,
    get_manual_adjustments
)
# 导入天气管理工具模块
from tools.weather_manager import (
    get_weather_by_search,
    get_typical_weather_by_season,
    detect_high_incidents_for_prediction,
    save_weather_workload_association,
    manual_adjust_weather,  # 新增：手动修改天气数据
    get_weather_adjustments,  # 新增：查询天气修改记录
    collect_historical_workload  # 新增：收集历史业务量数据
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
    remaining_steps: int


def _tool_call_parser(state: dict) -> dict:
    """
    解析 Ollama 模型返回的文本格式工具调用（如 <tool_call>...</tool_call>）
    转换为标准 AIMessage.tool_calls 格式，使框架能自动执行工具
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage):
        return state

    content = last_msg.content
    if not content or not isinstance(content, str):
        return state

    if '<tool_call>' not in content:
        return state

    # 提取 <tool_call> 和 </tool_call> 之间的完整内容（支持嵌套JSON）
    # 注意：不能使用 {.*?} 因为会匹配到嵌套括号中的第一个 }，导致JSON解析失败
    pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
    matches = re.findall(pattern, content, re.DOTALL)

    if not matches:
        return state

    tool_calls = []
    for i, match in enumerate(matches):
        try:
            call_data = json.loads(match.strip())
            tool_name = call_data.get("name", "")
            arguments = call_data.get("arguments", {})
            tool_calls.append({
                "name": tool_name,
                "args": arguments,
                "id": f"call_{i}_{tool_name}",
                "type": "tool_call"
            })
        except json.JSONDecodeError:
            continue

    if not tool_calls:
        return state

    # 去掉原始内容中的 <tool_call> 标签，保留正常文字
    cleaned_content = re.sub(r'<tool_call>.*?</tool_call>', '', content, flags=re.DOTALL).strip()
    # 如果清理后为空，用最后一条工具结果的信息做友好提示
    if not cleaned_content:
        cleaned_content = "根据查询结果，我已获取到相关数据，请您进一步说明想了解的具体内容。"

    # 创建新的 AIMessage
    new_msg = AIMessage(
        content=cleaned_content,
        tool_calls=tool_calls,
        additional_kwargs=last_msg.additional_kwargs,
        id=last_msg.id,
        response_metadata=last_msg.response_metadata
    )

    return {"messages": messages[:-1] + [new_msg]}


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

    if not api_key:
        raise ValueError(
            "❌ 缺少必要的环境变量: COZE_WORKLOAD_IDENTITY_API_KEY\n"
            "请在 .env 文件中设置: COZE_WORKLOAD_IDENTITY_API_KEY=<智谱API Key>\n"
            "智谱API Key获取: https://open.bigmodel.cn/usercenter/apikeys"
        )

    if not base_url:
        base_url = "https://open.bigmodel.cn/api/paas/v4/"
        print(f"⚠️  未设置 COZE_INTEGRATION_MODEL_BASE_URL，使用GLM默认值: {base_url}")

    # 初始化LLM
    llm_kwargs = {
        "model": cfg['config'].get("model"),
        "api_key": api_key,
        "base_url": base_url,
        "temperature": cfg['config'].get('temperature', 0.3),
        "streaming": True,
        "timeout": cfg['config'].get('timeout', 600),
    }
    # GLM-4-Flash 不需要 extra_body 和 default_headers
    llm = ChatOpenAI(**llm_kwargs)

    # 注册全部工具（从 config 中加载工具列表）
    _tool_map = {
        'get_historical_dispatch_data': get_historical_dispatch_data,
        'get_weather_forecast': get_weather_forecast,
        'get_holiday_info': get_holiday_info,
        'get_equipment_status': get_equipment_status,
        'fuse_multi_source_data': fuse_multi_source_data,
        'predict_dispatch_volume': predict_dispatch_volume,
        'analyze_prediction_trend': analyze_prediction_trend,
        'predict_with_time_series': predict_with_time_series,
        'evaluate_prediction_performance': evaluate_prediction_performance,
        'generate_staffing_decision': generate_staffing_decision,
        'optimize_shift_schedule': optimize_shift_schedule,
        'generate_decision_report': generate_decision_report,
        'get_schedule_staff_info': get_schedule_staff_info,
        'get_existing_schedule': get_existing_schedule,
        'generate_intelligent_schedule': generate_intelligent_schedule,
        'analyze_schedule_fairness': analyze_schedule_fairness,
        'export_schedule_report': export_schedule_report,
        'save_schedule_records': save_schedule_records,
        'get_realtime_workload_dashboard': get_realtime_workload_dashboard,
        'get_workload_weights_config': get_workload_weights_config,
        'analyze_staff_requirement': analyze_staff_requirement,
        'get_workload_by_module': get_workload_by_module,
        'predict_staffing_need': predict_staffing_need,
        'generate_staffing_recommendations': generate_staffing_recommendations,
        'evaluate_staff_efficiency': evaluate_staff_efficiency,
        'calculate_optimal_staffing': calculate_optimal_staffing,
        'assess_situation_awareness': assess_situation_awareness,
        'generate_situation_report': generate_situation_report,
        'get_situation_dashboard': get_situation_dashboard,
        'assess_comprehensive_risk': assess_comprehensive_risk,
        'generate_risk_alert_report': generate_risk_alert_report,
        'check_daily_risks': check_daily_risks,
        'calculate_plan_workload': calculate_plan_workload,
        'calculate_non_plan_workload': calculate_non_plan_workload,
        'get_workload_dashboard': get_workload_dashboard,
        'manual_adjust_plan_workload': manual_adjust_plan_workload,
        'get_manual_adjustments': get_manual_adjustments,
        'get_weather_by_search': get_weather_by_search,
        'get_typical_weather_by_season': get_typical_weather_by_season,
        'detect_high_incidents_for_prediction': detect_high_incidents_for_prediction,
        'save_weather_workload_association': save_weather_workload_association,
        'manual_adjust_weather': manual_adjust_weather,
        'get_weather_adjustments': get_weather_adjustments,
        'collect_historical_workload': collect_historical_workload,
    }
    tool_names = cfg.get("tools", [])
    tools = [_tool_map[name] for name in tool_names if name in _tool_map]

    # 追加中文输出规则
    chinese_output_rule = """

【最终回答铁律】
1. 所有工具调用完成后必须用中文写总结
2. 禁止输出JSON、代码块给用户
3. 禁止列出工具名称——直接调用即可
4. 用中文回复，保持简洁"""

    # 使用 config 中精简后的 sp
    sp = cfg.get("sp", "")
    sp = sp + chinese_output_rule

    # 创建Agent - 使用 post_model_hook 处理 Ollama 文本工具调用
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=sp,
        post_model_hook=_tool_call_parser,
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )

    return agent