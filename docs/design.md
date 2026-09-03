# 配网调度业务量智能预测系统 - 设计文档

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端层 (Frontend)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  HTML/CSS   │  │  JavaScript │  │     Chart.js        │ │
│  │  界面布局   │  │  业务逻辑   │  │     图表渲染        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
─────────────────────────────────────────────────────────────┘
                            ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                     后端层 (Backend)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   FastAPI   │  │  LangChain  │  │   LangGraph         │ │
│  │  REST API   │  │  Agent 框架 │  │   状态图            │ │
│  └─────────────┘  └─────────────┘  ─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    工具层 (Tools)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ 数据融合 │ │ 业务预测 │ │ 人员决策 │ │ 智能排班     │  │
│  ──────────┘ └──────────┘ ──────────┘ └──────────────┘  │
│  ┌──────────┐ ──────────┐ ┌──────────┐ ──────────────┐  │
│  │ 工作量   │ │ 人员预测 │ │ 态势感知 │ │ 风险预警     │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────
│                    数据层 (Data)                             │
│  ┌─────────────┐  ─────────────┐  ┌─────────────────────┐ │
│  │   Oracle    │  │  本地文件   │  │   向量知识库        │ │
│  │   数据库    │  │  (JSON/CSV) │  │   (ChromaDB)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 前端 | HTML5 + CSS3 + JavaScript | ES6+ | 界面展示和交互 |
| 前端 | Chart.js | 4.x | 图表渲染 |
| 后端 | Python | 3.12+ | 后端逻辑 |
| 后端 | FastAPI | 0.100+ | REST API 框架 |
| 后端 | LangChain | 1.0+ | AI Agent 框架 |
| 后端 | LangGraph | 1.0+ | 状态图编排 |
| 数据库 | Oracle | 11g+ | 业务数据存储 |
| 数据库 | ChromaDB | 1.5+ | 向量知识库 |
| AI 模型 | Ollama | 最新 | 本地模型服务 |
| AI 模型 | 火山引擎 | - | 云端模型服务 |
| 部署 | Docker | 20.10+ | 容器化部署 |

---

## 2. 模块设计

### 2.1 前端模块

#### 2.1.1 文件结构
```
frontend/
├── index.html          # 主页面
├── css/
│   ├── style.css       # 主样式文件
│   ── workload-modal.css  # 弹窗样式
├── js/
│   ├── app.js          # 主应用逻辑
│   ── charts.js       # 图表渲染逻辑
└── vendor/
    ├── chart.umd.min.js    # Chart.js 库
    ── github-dark.min.css # 代码高亮样式
```

#### 2.1.2 核心组件

**仪表盘组件 (Dashboard)**
- 职责：展示核心业务数据
- 数据源：`/api/workload_dashboard`
- 更新频率：实时/手动刷新

**图表组件 (Charts)**
- 职责：可视化业务数据
- 图表类型：柱状图、饼图、折线图、环形图
- 数据源：`/api/workload_dashboard` 中的 `charts` 字段

**弹窗组件 (Modals)**
- 职责：展示详细信息和编辑界面
- 类型：工作量详情、人员详情、风险预警、待办事项、知识库、天气

**AI 对话组件 (Chat)**
- 职责：自然语言交互
- 数据源：`/api/chat` (WebSocket/流式)
- 功能：数据查询、趋势分析、决策建议

#### 2.1.3 状态管理
```javascript
// 全局状态
let staffDetailData = null;        // 人员详情数据
let currentSelectedShift = '';     // 当前选中班次
let currentSelectedTeam = 'A';     // 当前选中班组
let workloadDetailData = null;     // 工作量详情数据
```

---

### 2.2 后端模块

#### 2.2.1 文件结构
```
src/
├── main.py              # FastAPI 主入口
├── agents/
│   └── agent.py         # LangChain Agent 定义
├── tools/
│   ├── data_fusion.py   # 数据融合工具
│   ├── prediction.py    # 业务预测工具
│   ├── time_series_prediction.py  # 时序预测工具
│   ├── decision.py      # 决策支持工具
│   ├── scheduling.py    # 智能排班工具
│   ├── workload_statistics.py     # 工作量统计工具
│   ├── staff_prediction.py        # 人员预测工具
│   ├── situation_awareness.py     # 态势感知工具
│   ├── risk_alert.py    # 风险预警工具
│   ├── plan_workload.py # 计划工作量工具
│   ── local_knowledge.py         # 本地知识库工具
├── storage/
│   ├── database/
│   │   ├── db.py        # 数据库连接管理
│   │   └── oracle_db.py # Oracle 数据库操作
│   └── memory/
│       └── memory_saver.py        # 记忆存储
└── utils/               # 工具函数
```

#### 2.2.2 API 设计

**RESTful API 规范**
- 基础路径：`/api`
- 请求格式：JSON
- 响应格式：`{"success": true/false, "data": {...}, "message": "..."}`
- 错误处理：HTTP 状态码 + 错误信息

**核心 API 列表**

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 工作量看板 | GET | `/api/workload_dashboard` | 获取工作量汇总数据 |
| 计划工作量详情 | GET | `/api/plan_workload_detail` | 获取计划工作量分类详情 |
| 非计划工作量详情 | GET | `/api/nonplan_workload_detail` | 获取非计划工作量分类详情 |
| 人员详情 | GET | `/api/staff/detail` | 获取班组人员详情 |
| 风险预警 | GET | `/api/risk_alerts` | 获取风险预警列表 |
| 今日待办 | GET | `/api/todos` | 获取待办事项列表 |
| 保存工作量 | POST | `/api/save_workload_override` | 保存工作量手动调整 |
| AI 对话 | POST | `/api/chat` | 流式 AI 对话 |
| 知识库搜索 | POST | `/api/knowledge/search` | 搜索知识库文档 |
| 知识库文档列表 | GET | `/api/knowledge/documents` | 获取文档列表 |
| 知识库添加文档 | POST | `/api/knowledge/documents` | 添加文档 |
| 知识库删除文档 | DELETE | `/api/knowledge/documents/{doc_id}` | 删除文档 |
| 知识库更新文档 | PUT | `/api/knowledge/documents/{doc_id}` | 更新文档 |

---

### 2.3 Agent 设计

#### 2.3.1 Agent 架构
```python
# Agent 状态
class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]

# Agent 构建
def build_agent(ctx=None):
    llm = ChatOpenAI(...)
    tools = [
        get_historical_dispatch_data,
        get_weather_forecast,
        predict_dispatch_volume,
        generate_staffing_decision,
        ...
    ]
    return create_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=tools,
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
```

#### 2.3.2 工具列表

| 工具名称 | 功能 | 输入 | 输出 |
|---------|------|------|------|
| `get_historical_dispatch_data` | 获取历史调度数据 | 日期范围 | 历史记录列表 |
| `get_weather_forecast` | 获取天气预报 | 日期、地区 | 天气数据 |
| `get_holiday_info` | 获取节假日信息 | 日期 | 节假日信息 |
| `get_equipment_status` | 获取设备状态 | 设备 ID | 设备状态 |
| `fuse_multi_source_data` | 多源数据融合 | 多源数据 | 融合数据 |
| `predict_dispatch_volume` | 预测业务量 | 融合数据 | 预测结果 |
| `analyze_prediction_trend` | 分析预测趋势 | 预测结果 | 趋势分析 |
| `predict_with_time_series` | 时序预测 | 历史数据 | 时序预测结果 |
| `generate_staffing_decision` | 生成人员决策 | 业务量预测 | 决策建议 |
| `optimize_shift_schedule` | 优化排班 | 人员信息 | 排班方案 |
| `get_schedule_staff_info` | 获取排班人员信息 | 日期 | 排班信息 |
| `get_realtime_workload_dashboard` | 获取实时工作量 | 日期 | 工作量数据 |
| `predict_staffing_need` | 预测人员需求 | 业务量 | 人员需求 |
| `assess_situation_awareness` | 态势感知评估 | 多源数据 | 态势报告 |
| `assess_comprehensive_risk` | 综合风险评估 | 多源数据 | 风险报告 |
| `calculate_plan_workload` | 计算计划工作量 | 日期 | 工作量统计 |
| `calculate_non_plan_workload` | 计算非计划工作量 | 日期 | 工作量统计 |
| `search_knowledge` | 搜索知识库 | 查询词 | 相关文档 |

#### 2.3.3 系统提示词
```markdown
# 角色定义
你是配网调度业务量智能预测系统的 AI 助手，专注于电力调度业务量预测和决策支持。

# 任务目标
帮助用户分析调度业务量趋势，提供人员配置建议，识别潜在风险。

# 能力
- 查询历史调度数据和实时工作量
- 预测未来业务量趋势
- 生成人员配置和排班建议
- 评估态势和风险
- 搜索知识库文档

# 过程
1. 理解用户问题
2. 调用相关工具获取数据
3. 分析数据并生成建议
4. 以清晰格式返回结果

# 输出格式
根据用户问题返回结构化数据或自然语言分析。
```

---

### 2.4 数据库设计

#### 2.4.1 连接管理
```python
# 数据库连接池
class OracleDB:
    def __init__(self):
        self.pool = None
    
    async def connect(self):
        # 创建连接池
        self.pool = await oracledb.create_pool(...)
    
    async def disconnect(self):
        # 关闭连接池
        if self.pool:
            await self.pool.close()
```

#### 2.4.2 数据访问层

项目采用 DAO（Data Access Object）模式，每个业务模块对应一个数据访问类：

```python
# 1. 工作量数据访问
class WorkloadDAO:
    async def get_daily_workload(self, date: str) -> List[Dict]:
        # 查询每日工作量统计
        ...
    
    async def get_workload_by_module(self, date: str) -> Dict:
        # 按模块查询工作量（计划/非计划）
        ...
    
    async def get_hourly_workload(self, date: str) -> List[Dict]:
        # 查询每小时工作量明细
        ...

# 2. 排班数据访问
class ScheduleDAO:
    async def get_schedule_records(self, start_date: str, end_date: str) -> List[Dict]:
        # 查询排班记录
        ...
    
    async def get_team_schedule(self, team_name: str, date: str) -> Dict:
        # 查询指定班组的排班
        ...
    
    async def get_staff_on_duty(self, date: str) -> List[Dict]:
        # 查询当值人员
        ...

# 3. 预测数据访问
class PredictionDAO:
    async def save_prediction_result(self, date: str, result: Dict) -> None:
        # 保存预测结果
        ...
    
    async def get_historical_predictions(self, start_date: str, end_date: str) -> List[Dict]:
        # 查询历史预测记录
        ...

# 4. 知识库数据访问
class KnowledgeDAO:
    async def search_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        # 向量搜索知识库文档
        ...
    
    async def add_document(self, title: str, content: str, metadata: Dict) -> str:
        # 添加文档到知识库
        ...
    
    async def delete_document(self, doc_id: str) -> bool:
        # 删除知识库文档
        ...

# 5. 风险预警数据访问
class RiskAlertDAO:
    async def get_active_alerts(self, date: str) -> List[Dict]:
        # 查询活跃风险预警
        ...
    
    async def create_alert(self, alert_type: str, description: str, level: str) -> str:
        # 创建风险预警
        ...

# 6. 设备数据访问
class EquipmentDAO:
    async def get_equipment_status(self, equipment_id: str) -> Dict:
        # 查询设备状态
        ...
    
    async def get_overload_equipment(self, date: str) -> List[Dict]:
        # 查询重过载设备
        ...

# 7. 天气数据访问
class WeatherDAO:
    async def get_weather_forecast(self, date: str, region: str) -> Dict:
        # 查询天气预报
        ...
    
    async def save_weather_data(self, date: str, data: Dict) -> None:
        # 保存天气数据
        ...
```

**DAO 层设计原则：**
- 每个 DAO 类对应一个业务领域
- 方法命名清晰，遵循 `get_*`、`save_*`、`create_*`、`delete_*` 规范
- 返回类型统一使用 `Dict` 或 `List[Dict]`
- 支持异步操作（`async/await`）

---

## 3. 数据流设计

### 3.1 工作量数据流
```
1. 前端请求 /api/workload_dashboard?target_date=2026-08-20
2. 后端调用 calculate_plan_workload() 和 calculate_non_plan_workload()
3. 工具查询数据库或返回假数据
4. 后端汇总数据并返回
5. 前端更新卡片和图表
```

### 3.2 AI 对话数据流
```
1. 前端发送 POST /api/chat {message: "今天业务量如何？"}
2. 后端创建 Agent 实例
3. Agent 调用相关工具（get_realtime_workload_dashboard）
4. 工具返回数据
5. Agent 分析数据并生成回复
6. 后端流式返回给前端
7. 前端显示 AI 回复
```

### 3.3 人员决策数据流
```
1. 前端请求 /api/staff/detail?team_name=A 班&date_str=2026-08-20
2. 后端调用 get_staff_detail()
3. 工具查询排班记录表
4. 返回班组详情、当值人员、休息人员
5. 前端渲染人员列表
```

---

## 4. 部署设计

### 4.1 Docker 架构
```dockerfile
FROM python:3.12-slim-bookworm

# 安装 Oracle Instant Client
COPY instantclient-basic-linux.x64-23.26.3.0.0.zip /tmp/
RUN unzip /tmp/instantclient.zip -d /opt/oracle && ...

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . /app
WORKDIR /app

# 启动服务
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000"]
```

### 4.2 环境配置
```env
# 模型配置
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://host.docker.internal:11434/v1

# 数据库配置
DB_TYPE=oracle
DB_HOST=10.111.134.209
DB_PORT=1521
DB_NAME=omscsdb
DB_USER=OMSCS1
DB_PASSWORD=omscs_oms123

# 测试模式
SKIP_DB=true  # 使用假数据
```

### 4.3 网络架构
```
─────────────┐     ┌─────────────┐     ┌─────────────┐
│   浏览器    │────▶│  Nginx/     │────▶│  FastAPI    │
│  (用户)     │     │  反向代理   │     │  (5000)     │
─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
            ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
            │   Oracle    │         │   Ollama    │         │  ChromaDB   │
            │   数据库    │         │   模型服务  │         │  向量库     │
            │  (1521)     │         │  (11434)    │         │  (8000)     │
            └─────────────┘         └─────────────┘         └─────────────┘
```

---

## 5. 安全设计

### 5.1 认证与授权
- API 接口：JWT Token 认证（可选）
- 数据库：用户名/密码认证
- 模型服务：API Key 认证

### 5.2 数据安全
- 敏感数据加密存储
- 数据库连接使用 TLS
- 操作日志记录

### 5.3 网络安全
- Docker 网络隔离
- 防火墙规则
- CORS 配置

---

## 6. 性能优化

### 6.1 前端优化
- 静态资源缓存（CSS/JS 版本号）
- 图表懒加载
- 虚拟滚动（大数据列表）

### 6.2 后端优化
- 数据库连接池
- API 响应缓存
- 异步处理

### 6.3 AI 优化
- 模型量化（Ollama）
- 提示词优化
- 工具调用缓存

---

## 7. 监控与日志

### 7.1 日志系统
- 应用日志：`/app/work/logs/bypass/app.log`
- 日志级别：DEBUG/INFO/WARNING/ERROR
- 日志格式：时间 + 级别 + 模块 + 消息

### 7.2 监控指标
- API 响应时间
- 数据库连接数
- 模型调用次数
- 错误率

---

## 附录

### 附录 A：配置项说明
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `COZE_WORKLOAD_IDENTITY_API_KEY` | 模型 API Key | - |
| `COZE_INTEGRATION_MODEL_BASE_URL` | 模型服务地址 | - |
| `DB_TYPE` | 数据库类型 | oracle |
| `DB_HOST` | 数据库主机 | localhost |
| `DB_PORT` | 数据库端口 | 1521 |
| `SKIP_DB` | 跳过数据库（假数据模式） | false |

### 附录 B：错误码定义
| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 附录 C：版本历史
| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-08-20 | 初始版本 |
