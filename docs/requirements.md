# 配网调度业务量智能预测系统 - 需求文档

## 1. 项目概述

### 1.1 项目背景
配网调度业务量智能预测系统是一个基于 AI 的智能决策支持平台，旨在通过多源数据融合、AI 预测算法和智能分析，为配网调度业务提供科学的工作量预测、人员配置建议、风险预警和态势感知能力。

### 1.2 项目目标
- **智能化预测**：基于历史数据和 AI 算法，准确预测未来调度业务量
- **科学决策**：提供人员配置建议，优化排班方案
- **风险管控**：实时识别和预警潜在风险
- **态势感知**：全面掌握配网调度业务运行状态
- **知识管理**：构建向量知识库，支持智能问答

### 1.3 目标用户
- 配网调度值班长
- 调度业务管理人员
- 系统运维人员

---

## 2. 功能需求

### 2.1 核心功能模块

#### 2.1.1 数据融合分析模块
**功能描述**：整合多源数据，为预测和决策提供数据基础

**功能列表**：
1. **历史调度数据查询** (`get_historical_dispatch_data`)
   - 查询指定日期范围的历史工作量数据
   - 支持按模块分类（计划/非计划）
   - 返回结构化数据供分析使用

2. **天气预报获取** (`get_weather_forecast`)
   - 查询指定日期和地区的天气预报
   - 包含温度、降水量、风力、极端天气等信息
   - 支持天气与工作量关联分析

3. **节假日信息查询** (`get_holiday_info`)
   - 查询指定日期是否为节假日
   - 支持节假日工作量模式识别

4. **设备状态查询** (`get_equipment_status`)
   - 查询设备运行状态
   - 识别重过载设备
   - 支持设备故障预警

5. **多源数据融合** (`fuse_multi_source_data`)
   - 整合历史数据、天气、节假日、设备状态
   - 生成融合后的特征数据
   - 为预测模型提供输入

#### 2.1.2 业务量预测模块
**功能描述**：基于 AI 算法预测未来调度业务量

**功能列表**：
1. **调度业务量预测** (`predict_dispatch_volume`)
   - 基于融合数据预测未来业务量
   - 支持单日和多日预测
   - 返回预测值和置信区间

2. **预测趋势分析** (`analyze_prediction_trend`)
   - 分析预测结果的趋势
   - 识别上升/下降/平稳趋势
   - 提供趋势解读和建议

3. **时间序列预测** (`predict_with_time_series`)
   - 使用时间序列算法进行预测
   - 支持 ARIMA、Prophet 等模型
   - 提高预测准确性

4. **预测性能评估** (`evaluate_prediction_performance`)
   - 评估预测模型的准确性
   - 计算 MAE、RMSE 等指标
   - 支持模型优化

#### 2.1.3 人员决策支持模块
**功能描述**：基于业务量预测生成人员配置建议

**功能列表**：
1. **人员决策生成** (`generate_staffing_decision`)
   - 根据预测业务量计算建议人数
   - 考虑天气、节假日等因素
   - 生成人员配置建议

2. **排班优化** (`optimize_shift_schedule`)
   - 优化现有排班方案
   - 平衡工作负荷
   - 提高人员利用率

3. **决策报告生成** (`generate_decision_report`)
   - 生成详细的人员决策报告
   - 包含数据分析和建议
   - 支持导出和分享

#### 2.1.4 智能排班模块
**功能描述**：管理和优化调度人员排班

**功能列表**：
1. **排班人员信息查询** (`get_schedule_staff_info`)
   - 查询指定班组的排班人员
   - 显示值班长和值班人员
   - 支持人员详情查看

2. **现有排班查询** (`get_existing_schedule`)
   - 查询指定日期范围的排班记录
   - 支持按班组筛选
   - 显示班次和时间

3. **智能排班生成** (`generate_intelligent_schedule`)
   - 基于业务量预测自动生成排班
   - 考虑人员技能和偏好
   - 优化排班公平性

4. **排班公平性分析** (`analyze_schedule_fairness`)
   - 分析排班的公平性
   - 识别工作负荷不均
   - 提供调整建议

5. **排班报告导出** (`export_schedule_report`)
   - 导出排班报告（Excel/PDF）
   - 支持自定义格式
   - 便于存档和分享

6. **排班记录保存** (`save_schedule_records`)
   - 保存排班记录到数据库
   - 支持批量导入
   - 数据持久化

#### 2.1.5 工作量统计模块
**功能描述**：实时统计和展示工作量数据

**功能列表**：
1. **实时工作量看板** (`get_realtime_workload_dashboard`)
   - 展示当日工作量汇总
   - 区分计划/非计划工作量
   - 显示开展中/已终结状态

2. **工作量权重配置** (`get_workload_weights_config`)
   - 配置各模块工作量权重
   - 支持自定义权重
   - 影响工作量计算

3. **人员需求分析** (`analyze_staff_requirement`)
   - 分析当前人员需求
   - 计算建议人数
   - 识别人员缺口

4. **按模块工作量统计** (`get_workload_by_module`)
   - 按业务模块统计工作量
   - 支持时间范围筛选
   - 生成统计图表

#### 2.1.6 人员需求预测模块
**功能描述**：预测未来人员需求

**功能列表**：
1. **人员需求预测** (`predict_staffing_need`)
   - 预测未来人员需求
   - 考虑业务量趋势
   - 生成需求报告

2. **人员建议生成** (`generate_staffing_recommendations`)
   - 生成具体的人员配置建议
   - 考虑技能和经验
   - 提供调整方案

3. **人员效率评估** (`evaluate_staff_efficiency`)
   - 评估人员工作效率
   - 计算工作量/人数比
   - 识别效率瓶颈

4. **最优人员配置计算** (`calculate_optimal_staffing`)
   - 计算最优人员配置
   - 平衡成本和效率
   - 提供优化建议

#### 2.1.7 态势感知模块
**功能描述**：全面感知配网调度业务运行状态

**功能列表**：
1. **态势感知评估** (`assess_situation_awareness`)
   - 评估当前业务态势
   - 识别异常和趋势
   - 生成态势报告

2. **态势报告生成** (`generate_situation_report`)
   - 生成详细的态势报告
   - 包含数据分析和解读
   - 支持导出和分享

3. **态势看板获取** (`get_situation_dashboard`)
   - 获取态势看板数据
   - 展示关键指标
   - 支持实时更新

#### 2.1.8 风险预警模块
**功能描述**：识别和预警潜在风险

**功能列表**：
1. **综合风险评估** (`assess_comprehensive_risk`)
   - 评估综合风险等级
   - 考虑多种风险因素
   - 生成风险报告

2. **风险预警报告生成** (`generate_risk_alert_report`)
   - 生成详细的风险预警报告
   - 包含风险描述和建议
   - 支持分级预警

3. **每日风险检查** (`check_daily_risks`)
   - 每日自动检查风险
   - 识别新增风险
   - 发送预警通知

#### 2.1.9 计划工作量统计模块
**功能描述**：统计和管理计划工作量

**功能列表**：
1. **计划工作量计算** (`calculate_plan_workload`)
   - 计算计划工作量
   - 包含周计划、设备投退、保供电等
   - 支持手动调整

2. **非计划工作量计算** (`calculate_non_plan_workload`)
   - 计算非计划工作量
   - 包含跳闸故障、异常缺陷、重过载等
   - 支持手动调整

3. **工作量看板获取** (`get_workload_dashboard`)
   - 获取工作量看板数据
   - 汇总计划/非计划工作量
   - 支持图表展示

4. **手动调整计划工作量** (`manual_adjust_plan_workload`)
   - 手动调整计划工作量
   - 记录调整原因
   - 支持审批流程

5. **手动调整记录查询** (`get_manual_adjustments`)
   - 查询手动调整记录
   - 支持时间范围筛选
   - 显示调整详情

#### 2.1.10 天气管理模块
**功能描述**：管理天气数据和工作量关联

**功能列表**：
1. **天气搜索** (`get_weather_by_search`)
   - 搜索指定地区的天气
   - 显示当前天气和未来预报
   - 支持极端天气预警

2. **典型天气查询** (`get_typical_weather_by_season`)
   - 查询典型季节天气
   - 用于预测模型训练
   - 支持历史天气分析

3. **高发事件检测** (`detect_high_incidents_for_prediction`)
   - 检测天气相关的高发事件
   - 识别天气对工作量的影响
   - 提供预警建议

4. **天气工作量关联保存** (`save_weather_workload_association`)
   - 保存天气与工作量的关联数据
   - 用于模型训练
   - 支持数据分析

5. **手动天气调整** (`manual_adjust_weather`)
   - 手动调整天气数据
   - 修正异常数据
   - 记录调整原因

6. **天气调整记录查询** (`get_weather_adjustments`)
   - 查询天气调整记录
   - 支持时间范围筛选
   - 显示调整详情

7. **历史工作量收集** (`collect_historical_workload`)
   - 收集历史工作量数据
   - 用于模型训练
   - 支持数据分析

#### 2.1.11 知识库模块
**功能描述**：构建和管理向量知识库

**功能列表**：
1. **知识库搜索** (`search_knowledge`)
   - 向量搜索知识库文档
   - 支持语义搜索
   - 返回相关文档和相似度

2. **知识库导入** (`import_knowledge`)
   - 导入文档到知识库
   - 支持多种格式（PDF、Word、TXT）
   - 自动向量化

#### 2.1.12 页面快照模块
**功能描述**：保存和读取页面状态

**功能列表**：
1. **页面快照读取** (`read_page_snapshot`)
   - 读取保存的页面状态
   - 支持恢复历史状态
   - 用于数据回溯

2. **页面快照保存** (后端 API: `/api/save_page_snapshot`)
   - 保存当前页面状态
   - 支持快照管理
   - 用于数据回溯

---

### 2.2 用户界面功能

#### 2.2.1 仪表盘布局
**功能描述**：主界面布局设计

**布局结构**：
1. **顶部导航栏**
   - 系统标题：业务态势感知智能体
   - 刷新按钮
   - 柔性值班计算按钮
   - 实时时钟显示

2. **核心数据卡片行（5 张卡片）**
   - 计划工作量卡片：显示总数、开展中/已终结
   - 非计划工作量卡片：显示总数、开展中/已终结
   - 当值班组卡片：显示班组名称、当值人数
   - 人员配置卡片：显示建议人数、超负荷状态
   - 天气状况卡片：显示温度、降水量、风力、极端天气

3. **图表区 + 右侧面板**
   - 左侧图表区（70%）：
     - 各模块业务情况（柱状图）
     - 操作票情况（饼图）
     - 各阶段业务工作量（折线图）
     - 网络发令情况（环形图）
   - 右侧面板（30%）：
     - 快速操作（4 个按钮）
     - 风险预警卡片
     - 今日待办卡片
     - 智能对话框

4. **系统状态栏**
   - 数据采集状态
   - AI 模型状态
   - 数据同步状态
   - 最后更新时间
   - 向量知识库按钮

#### 2.2.2 弹窗功能
**功能列表**：
1. **工作量详情弹窗**
   - 计划工作量详情：3 个分类输入框
   - 非计划工作量详情：3 个分类输入框
   - 保存按钮

2. **值班人员详情弹窗**
   - 当值班组、值班时间、班次显示
   - 建议人数、超负荷显示
   - 班次筛选（早/中/晚班）
   - 班组筛选（A/B/C/D/E 班）
   - 当值人员列表（可搜索）
   - 休息人员列表（可搜索）
   - 加入/移除当值按钮

3. **时间段详情弹窗**
   - 当前时间段显示
   - 当值人员数量
   - 班组人员工作量输入
   - 气象预警等级选择
   - 确认按钮

4. **风险预警详情弹窗**
   - 风险等级统计（高/中/低）
   - 风险详情列表
   - AI 深度分析按钮

5. **今日待办弹窗**
   - 待办事项列表
   - 状态标记（待处理/已完成）

6. **向量知识库弹窗**
   - 文档列表
   - 搜索框
   - 添加文档按钮

7. **天气详情弹窗**
   - 天气信息修改
   - 保存按钮

#### 2.2.3 交互功能
**功能列表**：
1. **卡片点击**
   - 计划/非计划工作量卡片：打开工作量详情弹窗
   - 当值班组/人员配置卡片：打开值班人员详情弹窗
   - 天气卡片：打开天气详情弹窗

2. **快速操作按钮**
   - 今日预测：发送预测请求
   - 7 天预测：发送 7 天预测请求
   - 人员建议：发送人员建议请求
   - 风险预警：发送风险预警请求

3. **智能对话**
   - 输入框：支持自然语言输入
   - 发送按钮：发送消息
   - 消息列表：显示对话历史
   - AI 思考加载动画

4. **图表交互**
   - 鼠标悬停显示详情
   - 点击图表元素筛选数据

---

### 2.3 后端 API 功能

#### 2.3.1 工作量 API
1. **GET /api/workload_dashboard**
   - 获取工作量看板数据
   - 参数：target_date（目标日期）
   - 返回：计划/非计划工作量、图表数据

2. **GET /api/plan_workload_detail**
   - 获取计划工作量详情
   - 参数：target_date（目标日期）
   - 返回：各分类工作量详情

3. **GET /api/nonplan_workload_detail**
   - 获取非计划工作量详情
   - 参数：target_date（目标日期）
   - 返回：各分类工作量详情

4. **POST /api/save_workload_override**
   - 保存工作量覆盖数据
   - 参数：target_date、workload_type、data
   - 返回：保存结果

#### 2.3.2 人员 API
1. **GET /api/staff/teams**
   - 获取班组列表
   - 返回：班组名称和人员数量

2. **GET /api/staff/detail**
   - 获取班组详情
   - 参数：team_name（班组名称）、date_str（日期）
   - 返回：当值人员、休息人员、班次信息

3. **POST /api/staff/temp/add**
   - 添加临时人员
   - 参数：team_name、person_id、person_name
   - 返回：添加结果

4. **POST /api/staff/temp/remove**
   - 移除临时人员
   - 参数：team_name、person_id
   - 返回：移除结果

5. **POST /api/staff/end_shift**
   - 结束值班
   - 参数：team_name、date_str
   - 返回：结束结果

#### 2.3.3 天气 API
1. **GET /api/weather**
   - 获取天气数据
   - 参数：date（日期）、region（地区）
   - 返回：天气信息

2. **POST /api/weather**
   - 保存天气数据
   - 参数：date、region、weather_data
   - 返回：保存结果

#### 2.3.4 知识库 API
1. **GET /api/knowledge/list**
   - 获取知识库文档列表
   - 返回：文档列表

2. **GET /api/knowledge/search**
   - 搜索知识库
   - 参数：query（查询词）、top_k（返回数量）
   - 返回：相关文档

3. **POST /api/knowledge/add**
   - 添加文档到知识库
   - 参数：title、content、metadata
   - 返回：文档 ID

4. **GET /api/knowledge/info**
   - 获取文档详情
   - 参数：doc_id（文档 ID）
   - 返回：文档信息

#### 2.3.5 风险预警 API
1. **GET /api/risk_alerts**
   - 获取风险预警列表
   - 参数：date（日期）
   - 返回：风险预警列表

2. **GET /api/todos**
   - 获取待办事项列表
   - 参数：date（日期）
   - 返回：待办事项列表

#### 2.3.6 预测 API
1. **GET /api/predict_workload**
   - 预测工作量
   - 参数：target_date（目标日期）、days（预测天数）
   - 返回：预测结果

#### 2.3.7 快照 API
1. **POST /api/save_page_snapshot**
   - 保存页面快照
   - 参数：snapshot_data
   - 返回：快照 ID

2. **GET /api/get_page_snapshot**
   - 获取页面快照
   - 参数：snapshot_id
   - 返回：快照数据

#### 2.3.8 系统 API
1. **GET /health**
   - 健康检查
   - 返回：服务状态

2. **GET /api/check_workload_updates**
   - 检查工作量更新
   - 参数：target_date
   - 返回：更新状态

3. **POST /api/apply_workload_updates**
   - 应用工作量更新
   - 参数：target_date、updates
   - 返回：应用结果

#### 2.3.9 AI 对话 API
1. **POST /run**
   - 运行 Agent
   - 参数：message（用户消息）
   - 返回：AI 回复

2. **POST /stream_run**
   - 流式运行 Agent
   - 参数：message（用户消息）
   - 返回：流式 AI 回复

3. **POST /cancel/{run_id}**
   - 取消运行
   - 参数：run_id（运行 ID）
   - 返回：取消结果

4. **POST /node_run/{node_id}**
   - 运行节点
   - 参数：node_id（节点 ID）、input（输入数据）
   - 返回：节点输出

5. **POST /v1/chat/completions**
   - OpenAI 兼容接口
   - 参数：messages（消息列表）
   - 返回：AI 回复

---

### 2.4 非功能需求

#### 2.4.1 性能需求
- 页面加载时间：< 3 秒
- API 响应时间：< 2 秒
- AI 回复时间：< 30 秒
- 图表渲染时间：< 1 秒
- 支持 100 并发用户

#### 2.4.2 可用性需求
- 系统可用性：99.9%
- 数据备份：每日自动备份
- 故障恢复：< 1 小时
- 支持离线模式（假数据）

#### 2.4.3 安全需求
- 用户认证：支持用户名/密码登录
- 权限控制：基于角色的访问控制
- 数据加密：敏感数据加密存储
- API 安全：防止 SQL 注入、XSS 攻击

#### 2.4.4 兼容性需求
- 浏览器：Chrome 90+、Firefox 88+、Edge 90+
- 操作系统：Windows 10/11、Linux、macOS
- 数据库：Oracle 11g+、MySQL 8.0+、PostgreSQL 13+
- Python：3.10+

#### 2.4.5 可扩展性需求
- 模块化设计：各功能模块独立、可替换
- 插件机制：支持自定义工具扩展
- 配置驱动：通过配置文件灵活调整参数
- API 标准化：便于第三方系统集成

---

## 3. 数据需求

### 3.1 数据库表结构

#### 3.1.1 工作量统计表
```sql
CREATE TABLE workload_statistics (
    id NUMBER PRIMARY KEY,
    stat_date DATE NOT NULL,
    module_name VARCHAR2(50) NOT NULL,
    workload_count NUMBER NOT NULL,
    in_progress_count NUMBER DEFAULT 0,
    completed_count NUMBER DEFAULT 0,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.1.2 排班记录表
```sql
CREATE TABLE schedule_records (
    id NUMBER PRIMARY KEY,
    team_name VARCHAR2(50) NOT NULL,
    shift_type VARCHAR2(20) NOT NULL,
    on_duty_time TIMESTAMP NOT NULL,
    team_leader_id VARCHAR2(50),
    team_leader_name VARCHAR2(100),
    person_ids VARCHAR2(500),
    person_names VARCHAR2(1000),
    schedule_status VARCHAR2(10) DEFAULT 'Y',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.1.3 预测结果表
```sql
CREATE TABLE prediction_results (
    id NUMBER PRIMARY KEY,
    predict_date DATE NOT NULL,
    predict_value NUMBER NOT NULL,
    confidence_level NUMBER,
    model_name VARCHAR2(50),
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.1.4 知识库文档表
```sql
CREATE TABLE knowledge_documents (
    id VARCHAR2(100) PRIMARY KEY,
    title VARCHAR2(200) NOT NULL,
    content CLOB,
    metadata CLOB,
    vector_data BLOB,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.1.5 风险预警表
```sql
CREATE TABLE risk_alerts (
    id NUMBER PRIMARY KEY,
    alert_date DATE NOT NULL,
    alert_type VARCHAR2(50) NOT NULL,
    alert_level VARCHAR2(20) NOT NULL,
    description VARCHAR2(500),
    suggestion VARCHAR2(500),
    status VARCHAR2(20) DEFAULT 'active',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.1.6 天气数据表
```sql
CREATE TABLE weather_data (
    id NUMBER PRIMARY KEY,
    weather_date DATE NOT NULL,
    region VARCHAR2(100) NOT NULL,
    temperature NUMBER,
    precipitation NUMBER,
    wind_speed NUMBER,
    extreme_weather VARCHAR2(50),
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.1.7 手动调整记录表
```sql
CREATE TABLE manual_adjustments (
    id NUMBER PRIMARY KEY,
    adjust_date DATE NOT NULL,
    workload_type VARCHAR2(50) NOT NULL,
    module_name VARCHAR2(50),
    original_value NUMBER,
    adjusted_value NUMBER,
    adjust_reason VARCHAR2(500),
    operator VARCHAR2(100),
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. 接口需求

### 4.1 外部系统集成

#### 4.1.1 Oracle 数据库
- 连接方式：JDBC/SQLAlchemy
- 认证：用户名/密码
- 数据：工作量统计、排班记录、预测结果

#### 4.1.2 大语言模型
- 支持模型：Ollama（本地）、GLM（云端）、其他 OpenAI 兼容模型
- 接口：OpenAI API 格式
- 功能：文本生成、对话、工具调用

#### 4.1.3 向量数据库
- 类型：ChromaDB
- 功能：文档向量化、语义搜索
- 用途：知识库管理

#### 4.1.4 天气 API
- 数据源：中国气象局/第三方天气服务
- 功能：天气预报查询
- 用途：工作量预测因子

---

## 5. 部署需求

### 5.1 环境要求
- **操作系统**：Linux（推荐 Ubuntu 20.04+）或 Windows 10/11
- **Python**：3.10+
- **Docker**：20.10+（可选）
- **内存**：8GB+（推荐 16GB）
- **存储**：50GB+

### 5.2 外部依赖
- **Oracle Instant Client**：19.21+ 或 23.26+
- **Ollama**：用于本地模型推理（可选）
- **Node.js**：16+（前端构建，可选）

### 5.3 配置文件
- `.env`：环境变量配置
- `config/agent_llm_config.json`：本地开发模型配置
- `config/agent_llm_config_docker.json`：Docker 容器模型配置
- `docker-compose.yml`：Docker 编排配置

### 5.4 部署模式
1. **生产模式**：连接 Oracle 数据库，使用真实数据
2. **测试模式**：使用假数据，无需数据库
3. **本地模式**：使用 Ollama 本地模型
4. **云端模式**：使用 GLM 等云端模型

---

## 6. 验收标准

### 6.1 功能验收
- [ ] 所有 12 个工具模块功能正常
- [ ] 所有 API 接口返回正确数据
- [ ] 前端界面显示正常，无 404 错误
- [ ] 弹窗功能正常，数据一致
- [ ] AI 对话功能正常，能正确调用工具

### 6.2 性能验收
- [ ] 页面加载时间 < 3 秒
- [ ] API 响应时间 < 2 秒
- [ ] AI 回复时间 < 30 秒
- [ ] 图表渲染时间 < 1 秒

### 6.3 数据验收
- [ ] 假数据与真实数据结构一致
- [ ] 卡片数据与弹窗数据一致
- [ ] 图表数据与 API 返回数据一致
- [ ] 数据库连接正常（生产模式）

### 6.4 安全验收
- [ ] 无 SQL 注入漏洞
- [ ] 无 XSS 攻击漏洞
- [ ] 敏感数据加密存储
- [ ] API 认证正常

---

## 附录

### A. 术语表
- **配网调度**：配电网络的调度管理
- **工作量**：调度业务的数量统计
- **计划工作量**：预先计划的调度业务
- **非计划工作量**：突发的调度业务（如故障）
- **态势感知**：对业务运行状态的全面感知
- **向量知识库**：基于向量化的文档知识库

### B. 参考资料
- Oracle 数据库文档：https://docs.oracle.com/
- LangChain 文档：https://python.langchain.com/
- FastAPI 文档：https://fastapi.tiangolo.com/
- Chart.js 文档：https://www.chartjs.org/

### C. 版本历史
- v1.0.0（2026-08-20）：初始版本，包含所有核心功能
