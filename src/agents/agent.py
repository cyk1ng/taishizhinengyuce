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
from langgraph.prebuilt import create_react_agent
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
    remaining_steps: int = 100  # 默认递归限制


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
        predict_with_time_series,  # 新增：基于Prophet/LSTM/XGBoost的时序预测
        evaluate_prediction_performance,  # 新增：预测性能评估
        
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
        save_schedule_records,
        
        # 工作量统计工具
        get_realtime_workload_dashboard,
        get_workload_weights_config,
        analyze_staff_requirement,
        get_workload_by_module,
        # 人员需求预测工具
        predict_staffing_need,
        generate_staffing_recommendations,
        evaluate_staff_efficiency,
        calculate_optimal_staffing,
        # 计划工作量统计工具（更新：包含计划工作量和非计划工作量）
        calculate_plan_workload,
        calculate_non_plan_workload,
        get_workload_dashboard,  # 新增：获取工作量看板数据（计划+非计划）
        manual_adjust_plan_workload,
        get_manual_adjustments,
        # 天气管理工具
        get_weather_by_search,  # 新增：通过搜索获取天气信息
        get_typical_weather_by_season,  # 新增：获取季节典型天气
        detect_high_incidents_for_prediction,  # 新增：检测高发事件
        save_weather_workload_association,  # 新增：保存天气-工作量关联数据
        manual_adjust_weather,  # 新增：手动修改天气数据
        get_weather_adjustments,  # 新增：查询天气修改记录
        collect_historical_workload,  # 新增：收集历史业务量数据
        # 风险预警工具
        assess_comprehensive_risk,  # 新增：综合风险评估
        generate_risk_alert_report,  # 新增：生成风险预警报告
        check_daily_risks,  # 新增：每日风险检查
        # 态势感知工具
        assess_situation_awareness,  # 新增：态势感知评估
        generate_situation_report,  # 新增：生成态势分析报告
        get_situation_dashboard  # 新增：获取态势看板数据
    ]
    
    # 创建Agent
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=cfg.get("sp"),
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
    
    return agent


# Agent元数据
AGENT_METADATA = {
    "name": "配网调度业务量智能预测Agent",
    "version": "2.0.0",
    "description": "基于多源数据融合和AI技术的配网调度业务量预测、人员决策支持、智能排班与工作量实时看板系统",
    "capabilities": [
        "多源数据融合",
        "业务量智能预测",
        "人员配置决策",
        "风险预警分析",
        "智能排班生成",
        "排班公平性分析",
        "排班方案优化",
        "实时工作量统计",
        "工作当量计算",
        "人力资源建议",
        "计划工作量统计",
        "非计划工作量统计",
        "天气信息管理",
        "天气分类（温度/降水/风力/极端天气）",
        "季节特点分析",
        "高发事件智能识别",
        "天气-工作量关联分析",
        "天气手动修改",
        "历史业务量收集（按高峰期/非高峰期分类）",
        "综合风险评估",
        "多维度风险识别",
        "风险预警报告生成",
        "每日风险检查",
        "态势感知评估",
        "运行态势分析",
        "态势趋势分析",
        "态势报告生成",
        "态势看板数据"
    ],
    "data_sources": [
        "历史调度记录",
        "天气预报",
        "节假日日历",
        "设备状态监控",
        "人员信息表(working_user)",
        "班组表(working_groups)",
        "排班记录表(work_schedule_recode)",
        "检修业务表(maintenance_records)",
        "故障日志表(fault_logs)",
        "缺陷记录表(defect_records)"
    ],
    "output_formats": [
        "JSON格式预测结果",
        "Markdown格式决策报告",
        "人员调整建议",
        "智能排班方案",
        "排班公平性报告",
        "实时工作量看板",
        "人力资源建议"
    ],
    "deployment_requirements": {
        "python_version": ">=3.10",
        "dependencies": [
            "langchain",
            "langgraph",
            "coze-coding-dev-sdk",
            "psycopg-binary"
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
