# 配网调度业务量智能预测系统 - 架构文档

## 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户交互层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Web界面     │  │  API接口     │  │  命令行工具  │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent应用层                                 │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │          配网调度业务量智能预测Agent                      │      │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │      │
│  │  │ 系统提示词  │  │ 工具编排    │  │ 状态管理    │     │      │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │      │
│  └──────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          工具层                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ 数据融合工具 │  │ 预测分析工具 │  │ 决策引擎工具 │             │
│  │              │  │              │  │              │             │
│  │ - 历史数据   │  │ - 业务预测   │  │ - 人员决策   │             │
│  │ - 天气数据   │  │ - 趋势分析   │  │ - 班次优化   │             │
│  │ - 节假日数据 │  │ - 风险评估   │  │ - 报告生成   │             │
│  │ - 设备状态   │  │              │  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        LLM服务层                                    │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │              大语言模型服务 (LLM API)                     │      │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │      │
│  │  │ 文本理解    │  │ 推理分析    │  │ 内容生成    │     │      │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │      │
│  └──────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         数据层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ PostgreSQL   │  │ Redis缓存    │  │ 对象存储     │             │
│  │ (历史数据)   │  │ (预测结果)   │  │ (报告文件)   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       外部数据源                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ 调度系统     │  │ 天气服务API  │  │ 设备监控系统 │             │
│  │ (历史记录)   │  │ (天气预报)   │  │ (实时状态)   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心模块详解

### 1. Agent层 (src/agents/)

**agent.py** - Agent主逻辑

```python
class AgentState(MessagesState):
    """Agent状态管理"""
    messages: Annotated[list[AnyMessage], _windowed_messages]

def build_agent(ctx=None):
    """构建Agent实例"""
    # 初始化LLM
    # 注册工具
    # 创建Agent
    return create_agent(...)
```

**职责**：
- 协调各工具模块
- 管理对话状态
- 处理用户请求
- 生成最终输出

### 2. 工具层 (src/tools/)

#### 2.1 数据融合模块 (data_fusion.py)

```python
# 工具列表
- get_historical_dispatch_data: 获取历史调度数据
- get_weather_forecast: 获取天气预报
- get_holiday_info: 获取节假日信息
- get_equipment_status: 获取设备状态
- fuse_multi_source_data: 多源数据融合
```

**数据流程**：

```
外部数据源 → 数据适配器 → 数据清洗 → 数据融合 → 标准化输出
```

#### 2.2 预测模块 (prediction.py)

```python
# 工具列表
- predict_dispatch_volume: 业务量预测
- analyze_prediction_trend: 趋势分析
```

**预测流程**：

```
融合数据 → 特征提取 → LLM推理 → 预测结果 → 置信度评估
```

#### 2.3 决策模块 (decision.py)

```python
# 工具列表
- generate_staffing_decision: 人员决策
- optimize_shift_schedule: 班次优化
- generate_decision_report: 报告生成
```

**决策流程**：

```
预测结果 → 需求计算 → 约束检查 → 方案生成 → 合规验证
```

### 3. 配置层 (config/)

**配置文件结构**：

```
config/
├── agent_llm_config.json      # Agent核心配置
├── data_sources.json           # 数据源配置
├── prediction_config.json      # 预测参数配置
└── decision_config.json        # 决策规则配置
```

**配置优先级**：

```
环境变量 > 配置文件 > 默认值
```

### 4. 存储层 (src/storage/)

```python
storage/
├── memory/          # 短期记忆存储
│   └── memory_saver.py
├── database/        # 数据库存储
│   └── db.py
└── s3/              # 对象存储
    └── s3_storage.py
```

## 数据流架构

### 主流程数据流

```
用户请求
    │
    ▼
Agent接收请求
    │
    ├──▶ 调用数据融合工具
    │       ├── 获取历史数据
    │       ├── 获取天气数据
    │       ├── 获取节假日数据
    │       └── 获取设备状态
    │           │
    │           ▼
    │       数据融合处理
    │           │
    │           ▼
    │       返回融合数据
    │
    ├──▶ 调用预测工具
    │       ├── 构建预测提示词
    │       ├── 调用LLM推理
    │       └── 解析预测结果
    │           │
    │           ▼
    │       返回预测数据
    │
    ├──▶ 调用决策工具
    │       ├── 计算人员需求
    │       ├── 生成调整方案
    │       └── 验证合规性
    │           │
    │           ▼
    │       返回决策建议
    │
    ▼
生成综合报告
    │
    ▼
返回给用户
```

## 技术栈

### 核心技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主要开发语言 |
| LangChain | 1.0.3 | Agent框架 |
| LangGraph | 1.0.2 | 状态管理 |
| OpenAI SDK | 2.24.0 | LLM接口 |

### 数据存储

| 技术 | 用途 |
|------|------|
| PostgreSQL | 持久化存储 |
| Redis | 缓存层 |
| S3 | 对象存储 |

### 外部集成

| 服务 | 接口类型 |
|------|----------|
| LLM API | REST API |
| 天气服务 | REST API |
| 设备监控 | REST API |
| 调度系统 | 数据库连接 |

## 性能优化

### 1. 缓存策略

```python
# Redis缓存配置
CACHE_CONFIG = {
    "historical_data": {
        "ttl": 3600,      # 1小时
        "key_prefix": "hist"
    },
    "weather_forecast": {
        "ttl": 7200,      # 2小时
        "key_prefix": "weather"
    },
    "prediction_result": {
        "ttl": 21600,     # 6小时
        "key_prefix": "pred"
    }
}
```

### 2. 并发处理

```python
# 异步处理示例
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def fetch_all_data_parallel(params):
    """并行获取多源数据"""
    with ThreadPoolExecutor(max_workers=4) as executor:
        loop = asyncio.get_event_loop()
        
        tasks = [
            loop.run_in_executor(executor, get_historical_data, params),
            loop.run_in_executor(executor, get_weather_data, params),
            loop.run_in_executor(executor, get_equipment_data, params)
        ]
        
        results = await asyncio.gather(*tasks)
    
    return results
```

### 3. 数据预处理

```python
# 历史数据预处理
def preprocess_historical_data(raw_data):
    """数据清洗和特征工程"""
    # 1. 缺失值处理
    # 2. 异常值检测
    # 3. 特征提取
    # 4. 数据标准化
    return processed_data
```

## 安全架构

### 1. 认证与授权

```
用户请求 → Token验证 → 权限检查 → 资源访问
```

### 2. 数据安全

- 敏感配置使用环境变量
- API密钥加密存储
- 数据传输使用HTTPS
- 日志脱敏处理

### 3. 访问控制

```python
# RBAC权限模型
PERMISSIONS = {
    "admin": ["all"],
    "operator": ["predict", "decision", "report"],
    "viewer": ["report"]
}
```

## 可扩展性设计

### 1. 插件化架构

```python
# 数据源插件接口
class DataSourcePlugin(ABC):
    @abstractmethod
    def fetch(self, params: Dict) -> Dict:
        """获取数据"""
        pass
    
    @abstractmethod
    def validate(self, data: Dict) -> bool:
        """验证数据"""
        pass
```

### 2. 模型扩展

支持多种LLM模型：

```python
SUPPORTED_MODELS = {
    "doubao-seed-1-8-251228": {
        "provider": "doubao",
        "capabilities": ["text", "vision"]
    },
    "deepseek-v3-2-251201": {
        "provider": "deepseek",
        "capabilities": ["text", "reasoning"]
    }
}
```

### 3. 算法扩展

预测算法可替换：

```python
class PredictionModel(ABC):
    @abstractmethod
    def predict(self, data: Dict) -> Dict:
        """执行预测"""
        pass

# 可选实现
- LLM-based Predictor (当前实现)
- Prophet Time Series
- ARIMA Model
- LSTM Neural Network
```

## 容错机制

### 1. 重试策略

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def call_llm_api(messages):
    """带重试的API调用"""
    return client.invoke(messages)
```

### 2. 降级方案

```python
def get_data_with_fallback(params):
    """带降级的数据获取"""
    try:
        # 优先从API获取
        return fetch_from_api(params)
    except Exception:
        # 降级到数据库
        return fetch_from_database(params)
    except Exception:
        # 最终降级到默认值
        return get_default_data()
```

### 3. 熔断机制

```python
class CircuitBreaker:
    """熔断器"""
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = "closed"
    
    def call(self, func, *args, **kwargs):
        if self.state == "open":
            raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self.failure_count = 0
            return result
        except Exception:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise
```

## 监控与日志

### 1. 性能监控

```python
# 关键指标
METRICS = {
    "prediction_accuracy": [],      # 预测准确率
    "response_time": [],            # 响应时间
    "api_success_rate": [],         # API成功率
    "resource_utilization": []      # 资源使用率
}
```

### 2. 日志规范

```python
import logging

# 结构化日志
logger = logging.getLogger(__name__)

logger.info(
    "Prediction completed",
    extra={
        "request_id": request_id,
        "prediction_days": 7,
        "confidence": 0.87,
        "execution_time": 2.3
    }
)
```

### 3. 链路追踪

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("predict") as span:
    span.set_attribute("prediction.horizon", 7)
    result = perform_prediction()
    span.set_attribute("prediction.confidence", result.confidence)
```

---

**文档版本**: v1.0.0  
**最后更新**: 2024-01-01
