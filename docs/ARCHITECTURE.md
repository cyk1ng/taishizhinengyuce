# 配网调度业务量智能预测系统 — 技术架构文档

## 1. 项目概览

**配网调度业务量智能预测系统**是一个面向电力配网调度场景的 AI 辅助决策平台，融合大语言模型（LLM）、时序预测、多源数据融合、实时看板展示等技术，为调度值班人员提供：
- 业务量实时看板（计划/非计划工作量统计）
- 业务量智能预测（LLM + 时序模型）
- 智能排班决策支持
- 风险预警与态势感知
- 天气与业务量的关联分析

### 1.1 核心架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户界面 (Frontend)                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  HTML5 看板  │  Chart.js 图表  │  AI 对话面板    │   │
│  └──────────┬───────────────────────────┬───────────┘   │
└──────────────┼───────────────────────────┼──────────────┘
               │                           │
┌──────────────▼───────────────────────────▼──────────────┐
│              FastAPI 后端 (Backend)                      │
│  ┌─────────────────┐  ┌────────────────────────────┐    │
│  │  REST API 路由   │  │  WebSocket Stream 接口     │    │
│  │  /api/*          │  │  /stream_run (SSE流式)     │    │
│  └────────┬────────┘  └────────────┬───────────────┘    │
└───────────┼─────────────────────────┼───────────────────┘
            │                         │
┌───────────▼─────────────────────────▼───────────────────┐
│              AI Agent 引擎层 (LangChain)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ChatOpenAI (GLM-4-Flash) ←→ LangChain Agent     │   │
│  │  System Prompt (详细业务规则 + 36个工具)          │   │
│  └──────────┬───────────────────────────────────────┘   │
└─────────────┼───────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────┐
│           工具层 / 数据层 (Tools & Storage)               │
│  ┌────────┬────────┬────────┬────────┬──────────────┐  │
│  │数据库  │记忆    │对象存储│工具函数│  Oracle RDS  │  │
│  │Postgres│Memory  │S3      │(时序/  │  (生产数据)  │  │
│  │(会话)  │Saver   │(文件)  │预测等)  │              │  │
│  └────────┴────────┴────────┴────────┴──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **前端** | HTML5 + CSS3 | - | 响应式看板页面 |
| | Chart.js | 4.x | 折线图/柱状图/饼图/仪表盘 |
| | markdown-it + highlight.js | - | AI回答的Markdown渲染与代码高亮 |
| | Fetch API / ReadableStream | - | SSE流式请求 |
| **后端** | Python | ≥3.12 | 主编程语言 |
| | FastAPI | ≥0.115 | REST API 框架 |
| | Uvicorn | ≥0.32 | ASGI 服务器 |
| | LangChain | ≥0.3 | Agent 框架 |
| | LangGraph | ≥0.2 | Agent 状态管理与记忆 |
| **AI** | ChatOpenAI (兼容模式) | - | 对接 GLM-4-Flash 模型 |
| | Prophet | ≥1.1.5 | 时序预测（趋势+季节性） |
| | XGBoost | ≥2.0 | 集成学习预测 |
| | PyTorch | ≥2.0 | LSTM 时序预测（可选） |
| **数据库** | PostgreSQL (psycopg) | ≥3.0 | 会话持久化与记忆存储 |
| | Oracle (cx_Oracle风格) | - | 生产业务数据查询 |
| | MemorySaver | - | 短期对话记忆（20轮滑动窗口） |
| **数据** | Pandas / NumPy | - | 数据处理与分析 |
| | SQLAlchemy | ≥2.0 | ORM 与数据库操作 |
| **存储** | S3 兼容对象存储 | - | 文件上传/报告导出 |
| **工具** | uv | - | Python 依赖管理 |

---

## 3. 目录结构

```
/workspace/projects/
├── config/
│   └── agent_llm_config.json      # LLM 模型配置（model/temperature/sp/tools）
├── docs/
│   └── ARCHITECTURE.md            # 本文档
├── assets/                        # 静态资源与测试数据
├── frontend/
│   ├── index.html                 # ✅ 主看板页面（单页应用）
│   ├── css/
│   │   ├── style.css              # 主样式（深蓝科技感主题）
│   │   └── workload-modal.css     # 弹窗样式
│   ├── js/
│   │   ├── app.js                 # ✅ 主应用逻辑（消息发送/模态框/API调用）
│   │   ├── api.js                 # API 封装（streamRun/REST调用）
│   │   └── charts.js              # ✅ 图表逻辑（4类图表初始化与更新）
│   └── assets/                    # 前端用静态资源
├── src/
│   ├── main.py                    # ✅ FastAPI 主入口（路由/静态文件/CORS）
│   ├── agents/
│   │   └── agent.py               # ✅ LangChain Agent 构建（36个工具注册）
│   ├── tools/                     # ✅ 工具模块（每个文件一个功能域）
│   │   ├── plan_workload.py       # 计划工作量统计（检修/投退/方式单/周计划/保供电）
│   │   ├── non_plan_workload.py   # 非计划工作量统计（故障/缺陷/重过载）
│   │   ├── workload_statistics.py # 工作量统计算法与看板生成
│   │   ├── data_fusion.py         # 多源数据融合（调度/天气/设备/人员）
│   │   ├── prediction.py          # LLM 预测模式
│   │   ├── time_series_prediction.py # 时序模型预测（Prophet/LSTM/XGBoost）
│   │   ├── decision.py            # 决策支持（人员配置/排班优化/报告生成）
│   │   ├── scheduling.py          # 智能排班（班组/角色/约束/公平性）
│   │   ├── staff_prediction.py    # 人员需求预测（效能/缺口/增员建议）
│   │   ├── risk_alert.py          # 风险预警（多维度评估/等级/报告）
│   │   ├── situation_awareness.py # 态势感知（综合态势/报告/看板）
│   │   ├── weather_manager.py     # 天气信息管理（分类/季节/关联分析）
│   │   └── weather_api.py         # 天气 API 封装
│   ├── storage/
│   │   ├── memory/
│   │   │   └── memory_saver.py    # ✅ 对话记忆（MemorySaver + Postgres 持久化）
│   │   ├── database/
│   │   │   └── db.py              # 数据库连接管理
│   │   └── s3/
│   │       └── s3_storage.py      # 对象存储封装
│   └── utils/
│       └── file/file.py           # 文件操作工具函数
├── scripts/                       # 脚手架脚本
├── pyproject.toml                 # ✅ 依赖声明（uv）
└── .gitignore                     # Git 忽略规则
```

---

## 4. 核心架构分层详解

### 4.1 前端层 (Frontend)

**技术选型：** 纯前端单页应用（SPA），无前端框架依赖。

| 文件 | 职责 | 核心函数 |
|------|------|----------|
| `index.html` | 整体页面布局：顶部header、左AI对话面板、中看板区域、右下预警/待办 | - |
| `style.css` | 深蓝科技感主题，响应式卡片布局，自定义滚动条，渐变背景 | - |
| `workload-modal.css` | 各弹窗样式（计划/非计划/天气/排班/排班详情/人员需求） | - |
| `app.js` | 主应用逻辑：AI对话管理、模态框控制、看板数据刷新 | `sendMessage()`, `loadRealTimeData()`, `updateDashboardWithData()`, `showPlanWorkloadModal()` |
| `charts.js` | 图表管理：初始化/更新/销毁 4类图表 | `initAllCharts()`, `updateWorkloadData()`, `initModuleBusinessChart()`, `initWorkloadTimelineChart()` |
| `api.js` | API 封装：SSE流式请求、REST请求 | `DispatchAPI.streamRun()`, `DispatchAPI.run()` |

**6 大看板卡片区域：**
1. **左上** — 允许工作量（计划任务统计 + 班次分配）
2. **左中** — 人员排班需求（人员配置/排班方案/效能分析）
3. **左下** — 天气预报（温度/降水/风力/极端天气设置）
4. **右上** — 非计划工作量（故障/缺陷/重过载统计）
5. **右中** — 今日预测（业务量预测趋势 + 人员缺口）
6. **右下** — 风险预警 & 今日待办（风险等级/待办事项清单）

**图表类型（4 种）：**
- 各阶段业务工作量折线图（`initWorkloadTimelineChart`）
- 各模块业务情况柱状图（`initModuleBusinessChart`）
- 人员需求/排班饼图（`initPieChart`）
- 人员需求甘特图/仪表盘（`initGaugeChart`）

**数据流：**
```
loadRealTimeData()
  └─ fetch('/api/workload_dashboard')
      └─ updateDashboardWithData(data)      ← 更新汇总卡片
          └─ updateWorkloadData(data)       ← 更新图表
              ├─ initWorkloadTimelineChart(data.hourly_details)
              └─ initModuleBusinessChart(data.moduleBusiness)
```

### 4.2 后端 API 层 (FastAPI)

**入口：** `src/main.py`（Uvicorn 启动，端口 5000）

| 路由 | 方法 | 用途 | 兜底策略 |
|------|------|------|----------|
| `/` | GET | 前端看板主页 | - |
| `/api/workload_dashboard` | GET | 看板总数据（summary + hourly + moduleBusiness） | 数据库空/异常 → mock |
| `/api/plan_workload_detail` | GET | 计划工作量详情（5模块+班次分配） | 数据库空/异常 → mock |
| `/api/nonplan_workload_detail` | GET | 非计划工作量详情（故障/缺陷/重过载明细） | 数据库空/异常 → mock |
| `/stream_run` | POST | AI Agent SSE 流式对话 | - |
| `/run` | POST | AI Agent 同步对话 | - |
| `/api/save_weather` | POST | 保存天气配置 | - |
| `/api/update_staff_config` | POST | 更新人员配置 | - |
| `/api/get_schedule` | GET | 获取排班方案 | - |
| `/health` | GET | 健康检查 | - |

**关键设计模式：**
- **Mock兜底策略**：所有查询数据库的接口都有两层兜底——① 数据库异常时返回 mock；② 数据库返回全零时也返回 mock
- **CORS 中间件**：允许跨域访问
- **静态文件挂载**：`/` 路由直接提供前端页面

### 4.3 AI Agent 层 (LangChain)

**入口：** `src/agents/agent.py`

| 组件 | 技术 | 配置 |
|------|------|------|
| LLM | ChatOpenAI（OpenAI兼容模式） | model=glm-4-flash, temperature=0.7, max_tokens=8000 |
| 系统提示词 | 自然语言规则 | 约 15KB 详细业务规则（36个工具 + 权重表 + 排班规则） |
| 工具注册 | `_tool_map` 字典 | 36个 @tool 装饰函数 |
| 状态管理 | LangGraph AgentState | 20轮对话滑动窗口（40条消息） |
| 记忆 | MemorySaver | 会话级短期记忆（PostgreSQL 持久化） |

**Agent 构建流程：**
```python
def build_agent(ctx=None):
    # 1. 读取模型配置 (config/agent_llm_config.json)
    # 2. 初始化 ChatOpenAI (GLM-4-Flash)
    # 3. 注册 36 个工具
    # 4. 配置 MemorySaver 记忆
    # 5. create_agent(model, tools, system_prompt, checkpointer, state_schema)
    # 6. return agent
```

**工作流程（15步）：**
1. 数据融合 → 2. 业务量预测 → 3. 人员需求预测 → 4. 获取人员信息 → 5. 排班 → 6. 计划工作量统计 → 7. 非计划工作量统计 → 8. 天气信息 → 9. 高发事件检测 → 10. 天气-工作量预测 → 11. 人力资源分析 → 12. 风险预警 → 13. 排班公平性 → 14. 保存 → 15. 决策报告

### 4.4 工具层 (Tools)

**36 个 @tool 装饰函数，按功能域分组：**

| 模块 | 文件 | 工具函数 | 用途 |
|------|------|----------|------|
| **数据融合** | `data_fusion.py` | `get_historical_dispatch_data`, `get_weather_forecast`, `get_holiday_info`, `get_equipment_status`, `fuse_multi_source_data` | 整合多源数据 |
| **预测** | `prediction.py` | `predict_dispatch_volume`, `analyze_prediction_trend` | LLM 预测模式 |
| **时序预测** | `time_series_prediction.py` | `predict_with_time_series`, `evaluate_prediction_performance` | Prophet/LSTM/XGBoost |
| **决策** | `decision.py` | `generate_staffing_decision`, `optimize_shift_schedule`, `generate_decision_report` | 决策支持 |
| **排班** | `scheduling.py` | `get_schedule_staff_info`, `get_existing_schedule`, `generate_intelligent_schedule`, `analyze_schedule_fairness`, `export_schedule_report`, `save_schedule_records` | 智能排班 |
| **工作量统计** | `workload_statistics.py` | `get_realtime_workload_dashboard`, `get_workload_weights_config`, `analyze_staff_requirement`, `get_workload_by_module` | 实时看板 |
| **计划工作量** | `plan_workload.py` | `calculate_plan_workload`, `calculate_non_plan_workload`, `get_workload_dashboard`, `manual_adjust_plan_workload`, `get_manual_adjustments` | 计划任务统计 |
| **非计划工作量** | `non_plan_workload.py` | - | 故障/缺陷/重过载查询 |
| **人员需求** | `staff_prediction.py` | `predict_staffing_need`, `generate_staffing_recommendations`, `evaluate_staff_efficiency`, `calculate_optimal_staffing` | 人员需求 |
| **风险预警** | `risk_alert.py` | `assess_comprehensive_risk`, `generate_risk_alert_report`, `check_daily_risks` | 风险评估 |
| **态势感知** | `situation_awareness.py` | `assess_situation_awareness`, `generate_situation_report`, `get_situation_dashboard` | 综合态势 |
| **天气管理** | `weather_manager.py` | `get_weather_by_search`, `get_typical_weather_by_season`, `detect_high_incidents_for_prediction`, `save_weather_workload_association`, `manual_adjust_weather`, `get_weather_adjustments`, `collect_historical_workload` | 天气管理 |
| **天气API** | `weather_api.py` | - | 天气数据API封装 |

---

## 5. 数据流详解

### 5.1 主看板数据流

```
[浏览器定时轮询 60s] → GET /api/workload_dashboard
                              │
                              ▼
                     main.py: workload_dashboard()
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
             数据库查询成功?         数据库查询失败?
              (数据>0条)              (异常或全零)
                    │                    │
                    ▼                    ▼
             解析 Oracle 表          返回 mock 数据
             → 聚合统计              (50计划+12非计划)
                    │                    │
                    └─────────┬──────────┘
                              ▼
                    JSON Response:
                    ├─ summary (汇总指标)
                    ├─ hourly_details (逐小时分布)
                    ├─ moduleBusiness (模块柱状图)
                    └─ plan_allocation (班次分配)
                              │
                              ▼
                    charts.js: updateWorkloadData()
                    ├─ initWorkloadTimelineChart(hourly)
                    └─ initModuleBusinessChart(moduleBusiness)
```

### 5.2 AI 对话数据流 (SSE)

```
[用户在聊天框输入] → POST /stream_run { message: "..." }
                            │
                            ▼
                    main.py: stream_run()
                    ┌─ agent = build_agent(ctx)
                    └─ agent.astream_events({messages: [...]})
                            │
                            ▼
                    SSE 事件流 (text/x-new-event)
                    ├─ on_chat_model_stream → 逐 token 推送给前端
                    ├─ on_tool_start → 工具调用通知
                    ├─ on_tool_end → 工具结果通知
                    └─ on_chain_end → 完整回复结束
                            │
                            ▼
                    [前端] ReadableStream 逐行读取
                    └─ appendMessage('ai', content)
```

---

## 6. 数据库架构

### 6.1 生产业务数据 (Oracle)

| 表名 | 业务含义 | 状态映射 |
|------|----------|----------|
| OP_MAINTENANCE_PLAN | 计划检修 | 执行中→开展中, 已完成/取消→已终结 |
| OP_TRANSFER_ORDER | 转供电 | 执行中/202→开展中, 已归档/203→已终结 |
| OP_EQUIPMENT_OPERATION | 设备投退 | 已许可→开展中, 已终结/已作废→已终结 |
| OP_WEEKLY_PLAN | 周计划 | 执行中→开展中, 已完成/已取消→已终结 |
| OP_PROTECT_FEEDER | 保供电 | REC/EXE/SQ/SP→开展中, CAN/END→已终结 |
| OC_FAULT_LOG | 故障日志 | 未交班(0)→待处理, 已交班(1)→已处理 |
| OC_DEFECT_RECORDS | 缺陷记录 | 未交班(0)→待处理, 已交班(1)→已处理 |
| OC_OVER_LOAD_LINE_LOG | 重过载 | 0/1→开展中, 2→已终结 |
| CS_SCHEDULING_RECORDS | 排班记录 | - |

### 6.2 会话持久化 (PostgreSQL)

- **用途**：LangGraph 对话记忆的持久化存储
- **管理**：`src/storage/memory/memory_saver.py` — `MemoryManager` 单例，带重试机制
- **连接配置**：通过 `COZE_WORKLOAD_IDENTITY_API_KEY` 等环境变量获取

### 6.3 对象存储 (S3)

- **用途**：排班报告导出文件的存储
- **封装**：`src/storage/s3/s3_storage.py`

---

## 7. 工作当量计算模型

### 7.1 权重体系

| 任务类型 | 权重 | 分类 |
|----------|------|------|
| 停电(电话下令) | 0.5 | 计划 |
| 停电(网络令) | 0.2 | 计划 |
| 复电(电话下令) | 0.75 | 计划 |
| 复电(网络令) | 0.3 | 计划 |
| 转供电 | 0.2 | 计划 |
| 周计划(带电) | 0.2 | 计划 |
| 周计划(投产) | 0.3 | 计划 |
| 设备投退 | 0.75 | 计划 |
| 跳闸重合成功 | 0.1 | 非计划 |
| 跳闸重合不成功(确定) | 0.3 | 非计划 |
| 跳闸重合不成功(不确定) | 0.5 | 非计划 |
| 母线接地 | 0.5 | 非计划 |
| 异常缺陷 | 0.5 | 非计划 |
| 重过载 | 0.1 | 非计划 |

### 7.2 计算公式

```
计划工作当量 = Σ(计划任务数 × 对应权重)
非计划工作当量 = Σ(非计划任务数 × 对应权重)
总工作当量 = 计划工作当量 + 非计划工作当量
需增派人数 = (工作当量 / (人均当量 × 1.5)) - 当值人数  （当工作当量 ≥ 人员当量 × 1.5时触发）
```

---

## 8. 排班引擎规则

### 8.1 班次定义

| 班次 | 时间 | 值 |
|------|------|-----|
| 晚班 | 00:00 - 08:00 | SHIFT_TYPE=1 |
| 早班 | 08:00 - 16:00 | SHIFT_TYPE=2 |
| 中班 | 16:00 - 24:00 | SHIFT_TYPE=3 |

### 8.2 人员配置约束

- **值班长**（ID_LEADER=3）：必须1人且只能1人
- **正值**（ID_LEADER=2）：至少1人，可多人
- **副值**（ID_LEADER=1）：至少1人，可多人
- **其他**（ID_LEADER=0）：可选

### 8.3 排班约束

- 同一班组一天只能排一个班次
- 最大连续工作天数：6天
- 每周最多晚班次数：3次
- 只安排"生效"状态的班组

---

## 9. 配置管理

### 9.1 模型配置 (`config/agent_llm_config.json`)

```json
{
  "config": {
    "model": "glm-4-flash",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 8000,
    "timeout": 600,
    "thinking": "disabled"
  },
  "sp": "...（15KB系统提示词，含完整业务规则）",
  "tools": ["get_historical_dispatch_data", ..., "check_daily_risks"]
}
```

### 9.2 环境变量

| 变量 | 用途 | 示例 |
|------|------|------|
| `COZE_WORKLOAD_IDENTITY_API_KEY` | LLM API Key | - |
| `COZE_INTEGRATION_MODEL_BASE_URL` | LLM 基础地址 | https://open.bigmodel.cn/api/paas/v4/ |
| `COZE_WORKSPACE_PATH` | 项目根目录 | /workspace/projects |

---

## 10. 前端交互要素

| 点击区域 | 触发函数 | 行为 |
|----------|----------|------|
| 计划工作量框 | `showPlanWorkloadModal()` | 弹窗显示5模块明细+班次分配 |
| 非计划工作量框 | `showNonPlanWorkloadModal()` | 弹窗显示故障/缺陷/重过载明细 |
| 排班框 | `showScheduleModal()` | 弹窗显示排班方案+人员信息 |
| 天气框 | `showWeatherModal()` | 弹窗设置温度/降水/风力/极端天气 |
| 人员排班需求框 | `showStaffModal()` | 弹窗显示人员需求分析+增员建议 |
| 排班详情框 | `showScheduleDetailModal()` | 弹窗显示详细排班表 |
| 今日预测框 | `showPredictionModal()` | 弹窗显示预测趋势+人员缺口 |
| 风险预警框 | `showRiskModal()` | 弹窗显示风险等级分布+预警列表 |
| 今日待办框 | `showTodoModal()` | 弹窗显示待办清单+完成状态切换 |
| AI聊天发送 | `sendMessage()` | SSE流式调用AI Agent |
| 快速按钮(左侧) | `quickAction(type)` | 自动填充提问并发送 |

---

## 11. 开发与部署

### 依赖管理

```bash
# 使用 uv（禁用 pip）
uv add <package_name>
uv pip list | grep -i <module>
```

### 启动

```bash
cd /workspace/projects
python src/main.py -m http -p 5000
# 浏览器访问 http://localhost:5000
```

### 测试

```bash
# 使用 test_run 工具测试 Agent 功能
test_run(params="查询今天的业务量")
```