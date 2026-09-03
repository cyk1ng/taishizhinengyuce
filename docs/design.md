# 配网调度业务量智能预测系统 - 设计文档

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                         │
├─────────────────────────────────────────────────────────────────┤
│  HTML/CSS/JavaScript  │  Chart.js  │  弹窗系统  │  状态管理     │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      后端层 (Backend)                            │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI  │  RESTful API  │  WebSocket  │  中间件  │  异常处理  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent 层 (AI Agent)                         │
├─────────────────────────────────────────────────────────────────┤
│  LangChain  │  ChatOpenAI  │  工具路由  │  记忆管理  │  提示词  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      工具层 (Tools)                              │
├─────────────────────────────────────────────────────────────────┤
│  数据融合  │  预测  │  排班  │  统计  │  风险  │  知识库  │  天气  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据层 (Data)                               │
├─────────────────────────────────────────────────────────────────┤
│  Oracle DB  │  ChromaDB  │  文件系统  │  环境变量  │  配置文件  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

#### 1.2.1 前端技术
- **HTML5**：页面结构
- **CSS3**：样式设计（Flexbox、Grid、动画）
- **JavaScript (ES6+)**：交互逻辑
- **Chart.js**：图表渲染（柱状图、饼图、折线图、环形图）
- **Fetch API**：HTTP 请求

#### 1.2.2 后端技术
- **Python 3.10+**：编程语言
- **FastAPI**：Web 框架
- **Uvicorn**：ASGI 服务器
- **SQLAlchemy**：ORM 框架
- **Pydantic**：数据验证

#### 1.2.3 AI 技术
- **LangChain**：Agent 框架
- **ChatOpenAI**：大语言模型接口
- **LangGraph**：状态图管理
- **ChromaDB**：向量数据库

#### 1.2.4 数据库
- **Oracle 11g+**：主数据库
- **oracledb**：Python Oracle 驱动

#### 1.2.5 部署
- **Docker**：容器化
- **Docker Compose**：编排
- **Oracle Instant Client**：数据库客户端

---

## 2. 模块设计

### 2.1 前端模块

#### 2.1.1 文件结构
```
frontend/
├── index.html              # 主页面
├── css/
│   ├── style.css           # 主样式
│   └── workload-modal.css  # 弹窗样式
├── js/
│   ├── app.js              # 主应用逻辑
│   └── charts.js           # 图表逻辑
└── vendor/
    ├── chart.umd.min.js    # Chart.js 库
    ── github-dark.min.css # 代码高亮样式
```

#### 2.1.2 核心组件

**1. 仪表盘组件 (Dashboard)**
```javascript
// 布局结构
<div class="dashboard">
    <header class="header">...</header>           // 顶部导航
    <div class="stats-row">...</div>              // 5 张核心卡片
    <div class="main-row">                        // 图表 + 右侧面板
        <div class="charts-area">...</div>        // 4 个图表
        <div class="right-panel">...</div>        // 快速操作 + 风险 + 待办 + 对话
    </div>
    <div class="system-status-bar">...</div>      // 系统状态栏
</div>
```

**2. 卡片组件 (StatCard)**
```javascript
// 计划工作量卡片
<div class="stat-card stat-plan" onclick="showWorkloadModal('plan')">
    <div class="stat-header">
        <span class="stat-icon">📋</span>
        <span class="stat-title">计划工作量</span>
    </div>
    <div class="stat-total">
        <span class="stat-number green" id="stat-plan-total">--</span>
    </div>
    <div class="stat-detail-row">
        <span id="stat-plan-in-progress">--</span> / 
        <span id="stat-plan-completed">--</span>
    </div>
</div>
```

**3. 图表组件 (ChartBox)**
```javascript
// 柱状图
<div class="chart-box chart-bar-box">
    <div class="chart-title-bar">
        <h3>各模块业务情况</h3>
        <span class="realtime-badge">实时更新</span>
    </div>
    <div class="chart-canvas-wrap">
        <canvas id="moduleBusinessChart"></canvas>
    </div>
</div>
```

**4. 弹窗组件 (Modal)**
```javascript
// 通用弹窗结构
<div id="modalId" class="modal-overlay hidden">
    <div class="modal-content large">
        <div class="modal-header">
            <h3>标题</h3>
            <button class="modal-close" onclick="closeModal('modalId')">&times;</button>
        </div>
        <div class="modal-body">
            <!-- 动态内容 -->
        </div>
        <div class="modal-footer">
            <button class="form-confirm-btn">确认</button>
        </div>
    </div>
</div>
```

#### 2.1.3 状态管理
```javascript
// 全局状态
let staffDetailData = null;           // 班组详情数据
let currentSelectedShift = '早班';    // 当前选中班次
let currentSelectedTeam = 'A';        // 当前选中班组

// 数据更新流程
1. 页面加载 → loadDashboardData()
2. API 请求 → fetch('/api/workload_dashboard')
3. 数据解析 → updateDashboardWithData(data)
4. UI 更新 → 更新卡片、图表、状态栏
```

#### 2.1.4 事件处理
```javascript
// 卡片点击
onclick="showWorkloadModal('plan')"      // 计划工作量
onclick="showWorkloadModal('non-plan')"  // 非计划工作量
onclick="showStaffDetail()"              // 值班人员
onclick="showRiskModal()"                // 风险预警
onclick="showTodoModal()"                // 今日待办
onclick="showKnowledgeModal()"           // 知识库

// 快速操作
onclick="sendQuickMessage('今日预测')"
onclick="sendQuickMessage('7 天预测')"
onclick="sendQuickMessage('人员建议')"
onclick="sendQuickMessage('风险预警')"

// 班组筛选
onclick="selectTeam('A')"
onclick="selectTeam('B')"
...

// 班次筛选
onclick="selectShift('早班')"
onclick="selectShift('中班')"
onclick="selectShift('晚班')"
```

---

### 2.2 后端模块

#### 2.2.1 文件结构
```
src/
├── main.py                 # FastAPI 主应用
├── agents/
│   └── agent.py            # Agent 构建
├── tools/                  # 工具模块（17 个）
│   ├── data_fusion.py      # 数据融合
│   ├── prediction.py       # 业务量预测
│   ├── time_series_prediction.py  # 时间序列预测
│   ├── decision.py         # 人员决策
│   ├── scheduling.py       # 智能排班
│   ├── workload_statistics.py     # 工作量统计
│   ├── staff_prediction.py        # 人员需求预测
│   ├── situation_awareness.py     # 态势感知
│   ├── risk_alert.py       # 风险预警
│   ├── plan_workload.py    # 计划工作量
│   ├── non_plan_workload.py       # 非计划工作量
│   ├── weather_api.py      # 天气 API
│   ├── weather_manager.py  # 天气管理
│   ├── knowledge_search.py # 知识库搜索
│   ├── local_knowledge.py  # 本地知识库
│   ── snapshot_reader.py  # 页面快照
── storage/
│   ├── memory/
│   │   └── memory_saver.py # 记忆管理
│   └── database/
│       └── db.py           # 数据库连接
└── oracle_db.py            # Oracle 数据库工具
```

#### 2.2.2 API 设计

**RESTful API 规范**：
```python
# GET 请求 - 查询数据
@app.get("/api/resource")
def get_resource(param: str):
    return {"success": True, "data": ...}

# POST 请求 - 创建/更新数据
@app.post("/api/resource")
def create_resource(data: dict):
    return {"success": True, "message": "..."}
```

**统一响应格式**：
```python
{
    "success": True/False,
    "data": {...},           # 成功时返回
    "message": "...",        # 失败时返回
    "error": "..."           # 错误详情
}
```

#### 2.2.3 中间件
```python
# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
```

---

### 2.3 Agent 设计

#### 2.3.1 Agent 架构
```python
def build_agent(ctx=None):
    # 1. 加载配置
    config = load_config("config/agent_llm_config.json")
    
    # 2. 初始化 LLM
    llm = ChatOpenAI(
        model=config['model'],
        api_key=api_key,
        base_url=base_url,
        temperature=config['temperature'],
        ...
    )
    
    # 3. 注册工具（35+ 个）
    tools = [
        read_page_snapshot,
        get_historical_dispatch_data,
        get_weather_forecast,
        ...
    ]
    
    # 4. 创建 Agent
    agent = create_agent(
        model=llm,
        system_prompt=config['sp'],
        tools=tools,
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
    
    return agent
```

#### 2.3.2 工具列表（35+ 个）

**数据融合工具（5 个）**：
1. `get_historical_dispatch_data` - 历史调度数据查询
2. `get_weather_forecast` - 天气预报获取
3. `get_holiday_info` - 节假日信息查询
4. `get_equipment_status` - 设备状态查询
5. `fuse_multi_source_data` - 多源数据融合

**预测工具（4 个）**：
6. `predict_dispatch_volume` - 调度业务量预测
7. `analyze_prediction_trend` - 预测趋势分析
8. `predict_with_time_series` - 时间序列预测
9. `evaluate_prediction_performance` - 预测性能评估

**决策工具（3 个）**：
10. `generate_staffing_decision` - 人员决策生成
11. `optimize_shift_schedule` - 排班优化
12. `generate_decision_report` - 决策报告生成

**排班工具（6 个）**：
13. `get_schedule_staff_info` - 排班人员信息查询
14. `get_existing_schedule` - 现有排班查询
15. `generate_intelligent_schedule` - 智能排班生成
16. `analyze_schedule_fairness` - 排班公平性分析
17. `export_schedule_report` - 排班报告导出
18. `save_schedule_records` - 排班记录保存

**工作量统计工具（4 个）**：
19. `get_realtime_workload_dashboard` - 实时工作量看板
20. `get_workload_weights_config` - 工作量权重配置
21. `analyze_staff_requirement` - 人员需求分析
22. `get_workload_by_module` - 按模块工作量统计

**人员需求预测工具（4 个）**：
23. `predict_staffing_need` - 人员需求预测
24. `generate_staffing_recommendations` - 人员建议生成
25. `evaluate_staff_efficiency` - 人员效率评估
26. `calculate_optimal_staffing` - 最优人员配置计算

**态势感知工具（3 个）**：
27. `assess_situation_awareness` - 态势感知评估
28. `generate_situation_report` - 态势报告生成
29. `get_situation_dashboard` - 态势看板获取

**风险预警工具（3 个）**：
30. `assess_comprehensive_risk` - 综合风险评估
31. `generate_risk_alert_report` - 风险预警报告生成
32. `check_daily_risks` - 每日风险检查

**计划工作量工具（5 个）**：
33. `calculate_plan_workload` - 计划工作量计算
34. `calculate_non_plan_workload` - 非计划工作量计算
35. `get_workload_dashboard` - 工作量看板获取
36. `manual_adjust_plan_workload` - 手动调整计划工作量
37. `get_manual_adjustments` - 手动调整记录查询

**天气管理工具（7 个）**：
38. `get_weather_by_search` - 天气搜索
39. `get_typical_weather_by_season` - 典型天气查询
40. `detect_high_incidents_for_prediction` - 高发事件检测
41. `save_weather_workload_association` - 天气工作量关联保存
42. `manual_adjust_weather` - 手动天气调整
43. `get_weather_adjustments` - 天气调整记录查询
44. `collect_historical_workload` - 历史工作量收集

**知识库工具（2 个）**：
45. `search_knowledge` - 知识库搜索
46. `import_knowledge` - 知识库导入

**页面快照工具（1 个）**：
47. `read_page_snapshot` - 页面快照读取

#### 2.3.3 系统提示词
```markdown
# 角色定义
你是配网调度业务量智能预测专家，专注于电力配网调度业务的数据分析、预测和决策支持。

# 任务目标
你的任务是分析配网调度业务数据，预测未来业务量趋势，提供人员配置建议，识别潜在风险，并生成详细的分析报告。

# 能力
- 多源数据融合：整合历史调度、天气、节假日、设备状态等数据
- 业务量预测：基于 AI 预测未来调度业务量趋势
- 人员决策支持：生成科学的值班人员调整建议
- 风险预警：识别异常和潜在风险，提供预警建议
- 智能排班：优化排班方案，提高人员利用率
- 态势感知：全面掌握配网调度业务运行状态
- 知识管理：构建向量知识库，支持智能问答

# 过程
1. 理解用户需求
2. 调用相关工具获取数据
3. 分析数据并生成洞察
4. 提供建议和决策支持
5. 生成报告或可视化结果

# 输出格式
根据用户需求返回相应的结果，可以是：
- 数据分析报告
- 预测结果和趋势
- 人员配置建议
- 风险预警信息
- 排班优化方案
- 知识库搜索结果
```

---

### 2.4 数据库设计

#### 2.4.1 数据库连接
```python
# Oracle 数据库连接
DATABASE_URL = "oracle+oracledb://user:password@host:port/?service_name=service"

# 连接池配置
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)
```

#### 2.4.2 数据访问层（DAO）

**1. WorkloadDAO - 工作量数据访问**
```python
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
```

**2. ScheduleDAO - 排班数据访问**
```python
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
```

**3. PredictionDAO - 预测数据访问**
```python
class PredictionDAO:
    async def save_prediction_result(self, date: str, result: Dict) -> None:
        # 保存预测结果
        ...
    
    async def get_historical_predictions(self, start_date: str, end_date: str) -> List[Dict]:
        # 查询历史预测记录
        ...
```

**4. KnowledgeDAO - 知识库数据访问**
```python
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
```

**5. RiskAlertDAO - 风险预警数据访问**
```python
class RiskAlertDAO:
    async def get_active_alerts(self, date: str) -> List[Dict]:
        # 查询活跃风险预警
        ...
    
    async def create_alert(self, alert_type: str, description: str, level: str) -> str:
        # 创建风险预警
        ...
```

**6. EquipmentDAO - 设备数据访问**
```python
class EquipmentDAO:
    async def get_equipment_status(self, equipment_id: str) -> Dict:
        # 查询设备状态
        ...
    
    async def get_overload_equipment(self, date: str) -> List[Dict]:
        # 查询重过载设备
        ...
```

**7. WeatherDAO - 天气数据访问**
```python
class WeatherDAO:
    async def get_weather_forecast(self, date: str, region: str) -> Dict:
        # 查询天气预报
        ...
    
    async def save_weather_data(self, date: str, data: Dict) -> None:
        # 保存天气数据
        ...
```

**DAO 层设计原则**：
- 每个 DAO 类对应一个业务领域
- 方法命名清晰，遵循 `get_*`、`save_*`、`create_*`、`delete_*` 规范
- 返回类型统一使用 `Dict` 或 `List[Dict]`
- 支持异步操作（`async/await`）

---

## 3. 数据流设计

### 3.1 工作量数据流
```
1. 前端请求 GET /api/workload_dashboard?target_date=2026-08-20
2. 后端调用 calculate_plan_workload() 和 calculate_non_plan_workload()
3. 工具查询数据库或返回假数据
4. 后端汇总数据并返回
5. 前端 updateDashboardWithData() 更新卡片
6. 前端 initModuleBusinessChart() 等更新图表
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
1. 前端请求 GET /api/staff/detail?team_name=A 班&date_str=2026-08-20
2. 后端调用 get_staff_detail()
3. 工具查询排班记录表
4. 返回班组详情、当值人员、休息人员
5. 前端渲染人员列表
```

### 3.4 风险预警数据流
```
1. 前端请求 GET /api/risk_alerts?date=2026-08-20
2. 后端调用 check_daily_risks()
3. 工具分析数据并识别风险
4. 返回风险预警列表
5. 前端渲染风险卡片
```

### 3.5 预测数据流
```
1. 前端请求 GET /api/predict_workload?target_date=2026-08-20&days=7
2. 后端调用 predict_dispatch_volume()
3. 工具融合多源数据
4. AI 模型生成预测结果
5. 返回预测数据和趋势
6. 前端渲染预测图表
```

---

## 4. 部署设计

### 4.1 Docker 架构
```
┌─────────────────────────────────────────┐
│           Docker Container              │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐   │
│  │         Python App              │   │
│  │  FastAPI + Uvicorn              │   │
│  │  Port: 5000                     │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────   │
│  │    Oracle Instant Client        │   │
│  │    /opt/oracle/instantclient    │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │      Frontend Files             │   │
│  │      /app/frontend              │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
         │                    │
         ▼                    ▼
    Host Network        Host Volume
    Port: 5000          /app/work/logs
```

### 4.2 环境配置

**生产模式（.env）**：
```env
# 模型配置 - 云端 GLM
COZE_WORKLOAD_IDENTITY_API_KEY=your_api_key
COZE_INTEGRATION_MODEL_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
COZE_MODEL_NAME=glm-4
COZE_TEMPERATURE=0.7
COZE_MAX_TOKENS=8000
COZE_TIMEOUT=600

# 数据库配置 - Oracle
DB_TYPE=oracle
DB_HOST=10.111.134.209
DB_PORT=1521
DB_NAME=omscsdb
DB_USER=OMSCS1
DB_PASSWORD=omscs_oms123
DATABASE_URL=oracle+oracledb://OMSCS1:omscs_oms123@10.111.134.209:1521/?service_name=omscsdb
```

**测试模式（.env）**：
```env
# 模型配置 - 本地 Ollama
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://host.docker.internal:11434/v1
COZE_MODEL_NAME=qwen2.5:7b
COZE_TEMPERATURE=0.7
COZE_MAX_TOKENS=8000
COZE_TIMEOUT=600

# 数据库配置 - 跳过
SKIP_DB=true
```

### 4.3 网络架构
```
┌──────────────┐     HTTP:5000     ┌──────────────┐
│   Browser    │ ────────────────→ │  FastAPI     │
│   (Client)   │ ←──────────────── │  Server      │
──────────────┘                   └──────────────┘
                                          │
                                          │ HTTP
                                          ▼
                                   ┌──────────────┐
                                   │  Ollama/GLM  │
                                   │  (LLM)       │
                                   └──────────────┘
                                          │
                                          │ SQL
                                          ▼
                                   ┌──────────────┐
                                   │  Oracle DB   │
                                   │  (Database)  │
                                   └──────────────┘
```

---

## 5. 安全设计

### 5.1 认证授权
- **API 认证**：支持 API Key 认证
- **用户认证**：支持用户名/密码登录（可扩展）
- **权限控制**：基于角色的访问控制（RBAC）

### 5.2 数据安全
- **敏感数据加密**：密码、API Key 等加密存储
- **SQL 注入防护**：使用参数化查询
- **XSS 防护**：输入验证和输出转义
- **CORS 配置**：限制跨域访问

### 5.3 网络安全
- **HTTPS**：生产环境使用 HTTPS
- **防火墙**：限制端口访问
- **日志审计**：记录所有 API 访问

---

## 6. 性能优化

### 6.1 前端优化
- **缓存策略**：静态资源缓存
- **懒加载**：图表和弹窗按需加载
- **代码分割**：JS 文件分割
- **CDN 加速**：第三方库使用 CDN

### 6.2 后端优化
- **连接池**：数据库连接池
- **缓存**：Redis 缓存（可扩展）
- **异步处理**：异步 API
- **负载均衡**：多实例部署（可扩展）

### 6.3 AI 优化
- **模型缓存**：LLM 响应缓存
- **工具缓存**：工具结果缓存
- **流式响应**：减少等待时间
- **超时控制**：防止长时间等待

---

## 7. 监控与日志

### 7.1 日志系统
```python
# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/app/work/logs/app.log'),
        logging.StreamHandler()
    ]
)
```

### 7.2 监控指标
- **API 响应时间**：平均响应时间、P99 响应时间
- **错误率**：4xx、5xx 错误率
- **并发数**：当前并发请求数
- **数据库连接**：连接池使用率
- **AI 调用**：LLM 调用次数、平均响应时间

### 7.3 健康检查
```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

---

## 附录

### A. 配置文件说明

**config/agent_llm_config.json**（本地开发）：
```json
{
  "config": {
    "model": "qwen2.5:14b",
    "ollama": true,
    "temperature": 0.7,
    "max_tokens": 8000,
    "timeout": 600
  },
  "sp": "你是配网调度业务量智能预测专家...",
  "tools": ["tool1", "tool2", ...]
}
```

**config/agent_llm_config_docker.json**（Docker 容器）：
```json
{
  "config": {
    "model": "qwen2.5:7b",
    "ollama": true,
    "temperature": 0.7,
    "max_tokens": 8000,
    "timeout": 600
  },
  "sp": "你是配网调度业务量智能预测专家...",
  "tools": ["tool1", "tool2", ...]
}
```

### B. 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| COZE_WORKLOAD_IDENTITY_API_KEY | API Key | "ollama" |
| COZE_INTEGRATION_MODEL_BASE_URL | 模型 Base URL | - |
| COZE_MODEL_NAME | 模型名称 | "qwen2.5:14b" |
| COZE_TEMPERATURE | 温度参数 | 0.7 |
| COZE_MAX_TOKENS | 最大 Token 数 | 8000 |
| COZE_TIMEOUT | 超时时间（秒） | 600 |
| DB_TYPE | 数据库类型 | "oracle" |
| DB_HOST | 数据库主机 | "localhost" |
| DB_PORT | 数据库端口 | 1521 |
| DB_NAME | 数据库名称 | "omscsdb" |
| DB_USER | 数据库用户 | "OMSCS1" |
| DB_PASSWORD | 数据库密码 | - |
| DATABASE_URL | 数据库连接 URL | - |
| SKIP_DB | 跳过数据库 | "false" |

### C. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0.0 | 2026-08-20 | 初始版本，包含所有核心功能 |
