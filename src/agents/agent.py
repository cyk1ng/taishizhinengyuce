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
import logging
from pathlib import Path

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

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
except ImportError:
    pass

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
# 导入计划工作量统计工具模块
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
    manual_adjust_weather,
    get_weather_adjustments,
    collect_historical_workload
)


logger = logging.getLogger(__name__)

# 配置文件路径
LLM_CONFIG = "config/agent_llm_config.json"


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
        logger.warning("未设置 COZE_INTEGRATION_MODEL_BASE_URL，使用GLM默认值: %s", base_url)

    # 初始化LLM - GLM-4-Flash 使用 OpenAI 兼容模式
    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        max_tokens=cfg['config'].get('max_tokens', 8000),
        streaming=False,   # 先关闭 streaming 排查问题
        timeout=cfg['config'].get('timeout', 600),
    )

    logger.info(
        "GLM请求参数: model=%s, base_url=%s, temperature=%s, max_tokens=%s",
        cfg['config'].get("model"), base_url,
        cfg['config'].get('temperature', 0.7),
        cfg['config'].get('max_tokens', 8000)
    )

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

    logger.info("工具数量: %d个", len(tools))
    logger.info("系统提示词长度: %d字符", len(cfg.get("sp", "")))

    # 创建Agent
    # GLM-4-Flash 原生支持 tool_calls，无需 post_model_hook/middleware
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=cfg.get("sp", ""),
        checkpointer=get_memory_saver(),
        debug=True,   # 开启调试模式
    )

    return agent