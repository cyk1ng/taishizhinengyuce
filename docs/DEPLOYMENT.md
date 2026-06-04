# 配网调度业务量智能预测系统 - 部署与移植指南

## 📋 目录

1. [系统概述](#系统概述)
2. [环境要求](#环境要求)
3. [快速部署](#快速部署)
4. [本地移植指南](#本地移植指南)
5. [配置说明](#配置说明)
6. [数据源接入](#数据源接入)
7. [API接口文档](#api接口文档)
8. [运维指南](#运维指南)

---

## 系统概述

### 核心功能

本系统基于**多源数据融合**和**人工智能技术**，实现配网调度业务量智能预测与人员决策支持：

- ✅ **多源数据融合**：整合历史调度记录、天气数据、节假日信息、设备状态等
- ✅ **业务量智能预测**：基于AI模型预测未来调度业务量趋势
- ✅ **人员决策支持**：生成科学的值班人员调整建议
- ✅ **风险预警分析**：识别业务量异常和潜在风险

### 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    配网调度智能预测系统                      │
├─────────────────────────────────────────────────────────────┤
│  应用层：Agent接口、决策报告、预警推送                      │
├─────────────────────────────────────────────────────────────┤
│  决策层：人员配置引擎、班次优化、成本分析                   │
├─────────────────────────────────────────────────────────────┤
│  预测层：业务量预测、趋势分析、风险评估                     │
├─────────────────────────────────────────────────────────────┤
│  数据层：历史调度、天气、节假日、设备状态                   │
└─────────────────────────────────────────────────────────────┘
```

### 模块结构

```
src/
├── agents/
│   └── agent.py              # Agent主逻辑
├── tools/
│   ├── data_fusion.py        # 多源数据融合
│   ├── prediction.py         # 业务量预测
│   └── decision.py           # 人员决策引擎
├── storage/                  # 存储模块
└── utils/                    # 工具函数
config/
├── agent_llm_config.json     # Agent配置
├── data_sources.json         # 数据源配置
├── prediction_config.json    # 预测模型配置
└── decision_config.json      # 决策规则配置
assets/
└── holiday_calendar.json     # 节假日日历
```

---

## 环境要求

### 系统要求

- **操作系统**: Linux / macOS / Windows
- **Python版本**: ≥ 3.10
- **内存**: ≥ 8GB
- **存储**: ≥ 10GB

### 必需软件

- Python 3.10+
- PostgreSQL 12+ (可选，用于持久化存储)
- Redis (可选，用于缓存)

### Python依赖

核心依赖（已包含在`requirements.txt`中）：

```txt
langchain==1.0.3
langgraph==1.0.2
langchain-openai==1.0.1
coze-coding-dev-sdk==0.5.11
psycopg2-binary==2.9.9
```

---

## 快速部署

### 1. 克隆项目

```bash
git clone <项目地址>
cd dispatch-prediction-system
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建`.env`文件：

```bash
# LLM配置（必填）
COZE_WORKLOAD_IDENTITY_API_KEY=your_api_key
COZE_INTEGRATION_MODEL_BASE_URL=https://api.example.com

# 数据库配置（可选）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dispatch_db
DB_USER=postgres
DB_PASSWORD=password

# 天气API配置（可选）
WEATHER_API_ENDPOINT=https://api.weather.example.com
WEATHER_API_KEY=your_weather_api_key

# 设备监控API配置（可选）
EQUIPMENT_API_ENDPOINT=https://equipment.example.com/api
EQUIPMENT_AUTH_TOKEN=your_token
```

### 4. 初始化数据库（可选）

如果使用PostgreSQL存储：

```bash
python scripts/init_db.py
```

### 5. 启动服务

```bash
# 方式1：直接运行
python src/main.py

# 方式2：使用脚本
bash scripts/local_run.sh
```

### 6. 验证部署

```bash
# 运行测试
pytest tests/

# 或使用Agent测试工具
python -c "from agents.agent import build_agent; print('部署成功！')"
```

---

## 本地移植指南

### 移植前置条件

在将系统移植到本地服务器或终端前，请确保：

1. ✅ 本地环境满足[环境要求](#环境要求)
2. ✅ 准备好数据源访问权限
3. ✅ 获取LLM API访问凭证
4. ✅ 了解本地配网调度业务规则

### 移植步骤

#### 步骤1：数据源适配

**1.1 历史调度数据**

编辑 `src/tools/data_fusion.py`，替换 `HistoricalDataGenerator` 类：

```python
# 原始示例代码
@staticmethod
def generate_sample_data(start_date: datetime, end_date: datetime) -> List[Dict]:
    # ...示例数据生成逻辑

# 替换为实际数据库查询
import psycopg2

@staticmethod
def get_historical_data(start_date: datetime, end_date: datetime) -> List[Dict]:
    """从本地数据库获取历史调度数据"""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    
    cursor = conn.cursor()
    query = """
        SELECT 
            date,
            dispatch_count,
            fault_count,
            avg_duration_minutes,
            equipment_count
        FROM dispatch_records
        WHERE date BETWEEN %s AND %s
        ORDER BY date
    """
    
    cursor.execute(query, (start_date, end_date))
    
    records = []
    for row in cursor.fetchall():
        records.append({
            "date": row[0].strftime("%Y-%m-%d"),
            "dispatch_count": row[1],
            "fault_count": row[2],
            "avg_duration_minutes": float(row[3]),
            "equipment_count": row[4]
        })
    
    conn.close()
    return records
```

**数据字段要求**：

| 字段名 | 类型 | 说明 | 必需 |
|--------|------|------|------|
| date | string | 日期 (YYYY-MM-DD) | ✅ |
| dispatch_count | int | 调度次数 | ✅ |
| fault_count | int | 故障次数 | ✅ |
| avg_duration_minutes | float | 平均处理时长(分钟) | ⭕ |
| equipment_count | int | 涉及设备数量 | ⭕ |

**1.2 天气数据接入**

编辑 `src/tools/data_fusion.py`，替换 `WeatherDataGenerator` 类：

```python
import requests

@staticmethod
def get_weather_forecast(days: int = 7) -> List[Dict]:
    """从本地天气服务获取预报数据"""
    api_key = os.getenv("WEATHER_API_KEY")
    endpoint = os.getenv("WEATHER_API_ENDPOINT")
    
    # 示例：调用本地天气API
    url = f"{endpoint}/forecast?days={days}&key={api_key}"
    response = requests.get(url, timeout=30)
    
    if response.status_code != 200:
        raise ValueError(f"天气API调用失败: {response.status_code}")
    
    data = response.json()
    
    # 转换为标准格式
    forecast = []
    for item in data.get("forecast", []):
        forecast.append({
            "date": item["date"],
            "weather": item["condition"],
            "temperature_max": item["temp_max"],
            "temperature_min": item["temp_min"],
            "humidity": item["humidity"],
            "wind_level": item["wind_speed"],
            "rain_probability": item.get("rain_prob", 0)
        })
    
    return forecast
```

**数据字段要求**：

| 字段名 | 类型 | 说明 | 必需 |
|--------|------|------|------|
| date | string | 日期 (YYYY-MM-DD) | ✅ |
| weather | string | 天气状况（晴/多云/雨等） | ✅ |
| temperature_max | int | 最高温度(℃) | ✅ |
| temperature_min | int | 最低温度(℃) | ✅ |
| humidity | int | 湿度(%) | ⭕ |
| wind_level | int | 风力等级 | ⭕ |
| rain_probability | int | 降雨概率(0-100) | ⭕ |

**1.3 节假日日历**

更新 `assets/holiday_calendar.json`：

```json
{
  "2025": {
    "01-01": "元旦",
    "01-28": "春节",
    "01-29": "春节",
    ...
  },
  "metadata": {
    "last_updated": "2025-01-01",
    "source": "本地节假日数据",
    "note": "根据当地实际情况更新"
  }
}
```

或接入节假日API：

```python
# 在 data_fusion.py 中添加
import requests

def fetch_holidays_from_api(year: int) -> Dict:
    """从节假日API获取数据"""
    url = f"https://holiday-api.example.com/holidays?year={year}"
    response = requests.get(url, timeout=30)
    return response.json()
```

**1.4 设备状态数据**

编辑 `src/tools/data_fusion.py`，替换 `get_equipment_status` 工具：

```python
@tool
def get_equipment_status(runtime: ToolRuntime = None) -> str:
    """获取设备运行状态"""
    ctx = runtime.context if runtime else new_context(method="get_equipment_status")
    
    try:
        # 调用本地设备监控系统API
        endpoint = os.getenv("EQUIPMENT_API_ENDPOINT")
        token = os.getenv("EQUIPMENT_AUTH_TOKEN")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{endpoint}/status",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise ValueError(f"设备API调用失败: {response.status_code}")
        
        equipment_data = response.json()
        
        # 转换为标准格式
        equipment_list = []
        for eq in equipment_data.get("equipment", []):
            equipment_list.append({
                "id": eq["id"],
                "type": eq["type"],
                "status": eq["status"],
                "load_rate": eq["load_rate"],
                "last_maintenance": eq["last_maintenance_date"],
                "fault_probability": eq.get("fault_prob", 0.01)
            })
        
        result = {
            "success": True,
            "data_source": "local_equipment_monitoring",
            "timestamp": datetime.now().isoformat(),
            "total_equipment": len(equipment_list),
            "status_summary": {
                "normal": sum(1 for e in equipment_list if e["status"] == "正常"),
                "warning": sum(1 for e in equipment_list if e["status"] == "警告"),
                "fault": sum(1 for e in equipment_list if e["status"] == "故障")
            },
            "equipment_list": equipment_list
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取设备状态失败"
        }, ensure_ascii=False)
```

#### 步骤2：配置文件适配

**2.1 数据源配置**

编辑 `config/data_sources.json`：

```json
{
  "historical_data": {
    "enabled": true,
    "source_type": "database",
    "connection": {
      "host": "your_db_host",
      "port": 5432,
      "database": "your_db_name",
      "table": "dispatch_records",
      "username": "your_db_user",
      "password": "your_db_password"
    }
  },
  "weather": {
    "enabled": true,
    "source_type": "api",
    "api_endpoint": "https://your-weather-api.com",
    "api_key": "your_api_key"
  },
  ...
}
```

**2.2 预测参数调优**

编辑 `config/prediction_config.json`，根据本地业务特点调整：

```json
{
  "factors": {
    "weather_impact": {
      "weight": 0.3,
      "high_temperature_threshold": 38,  // 根据当地气候调整
      "heavy_rain_conditions": ["大雨", "暴雨", "特大暴雨"]
    },
    "seasonal_impact": {
      "peak_months": [7, 8, 12],  // 根据当地业务高峰期调整
      "peak_factor": 1.3
    }
  }
}
```

**2.3 决策规则配置**

编辑 `config/decision_config.json`，根据本地调度规则调整：

```json
{
  "staffing_rules": {
    "base_ratio": {
      "dispatches_per_person": 10,  // 根据当地业务能力调整
      "faults_per_person": 2,
      "emergency_buffer_ratio": 0.15
    },
    "shift_structure": {
      "shifts_per_day": 3,
      "shift_names": ["白班", "中班", "夜班"],
      "shift_times": {
        "白班": "08:00-16:00",
        "中班": "16:00-24:00",
        "夜班": "00:00-08:00"
      }
    }
  },
  "constraints": {
    "max_work_hours_per_day": 12,
    "max_consecutive_work_days": 6,
    "labor_law_reference": "《本地劳动法》相关条款"
  }
}
```

#### 步骤3：环境变量配置

创建本地环境变量文件 `.env.local`：

```bash
# === 必需配置 ===
# LLM API配置
COZE_WORKLOAD_IDENTITY_API_KEY=your_local_api_key
COZE_INTEGRATION_MODEL_BASE_URL=https://your-llm-api.com

# === 数据源配置 ===
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dispatch_system
DB_USER=postgres
DB_PASSWORD=your_password

# 天气API
WEATHER_API_ENDPOINT=https://api.weather.local
WEATHER_API_KEY=your_weather_key

# 设备监控
EQUIPMENT_API_ENDPOINT=https://equipment.local/api
EQUIPMENT_AUTH_TOKEN=your_token

# === 可选配置 ===
# 缓存
REDIS_HOST=localhost
REDIS_PORT=6379

# 日志
LOG_LEVEL=INFO
LOG_FILE=/var/log/dispatch_prediction/app.log
```

#### 步骤4：测试验证

**4.1 单元测试**

```bash
# 测试数据融合模块
pytest tests/test_data_fusion.py -v

# 测试预测模块
pytest tests/test_prediction.py -v

# 测试决策模块
pytest tests/test_decision.py -v
```

**4.2 集成测试**

```python
# tests/test_integration.py
from datetime import datetime, timedelta
from tools.data_fusion import fuse_multi_source_data
from tools.prediction import predict_dispatch_volume
from tools.decision import generate_staffing_decision

def test_full_workflow():
    """测试完整工作流"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # 1. 数据融合
    fused_data = fuse_multi_source_data.invoke({
        "start_date": start_date,
        "end_date": end_date
    })
    assert "success" in fused_data
    
    # 2. 业务量预测
    prediction = predict_dispatch_volume.invoke({
        "start_date": start_date,
        "end_date": end_date,
        "prediction_days": 7
    })
    assert "prediction" in prediction
    
    # 3. 人员决策
    decision = generate_staffing_decision.invoke({
        "prediction_result": prediction,
        "current_staff_count": 10
    })
    assert "decision" in decision
    
    print("✅ 集成测试通过")
```

**4.3 性能测试**

```bash
# 压力测试
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

#### 步骤5：生产部署

**5.1 使用Docker部署**

创建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "src/main.py"]
```

构建并运行：

```bash
# 构建镜像
docker build -t dispatch-prediction:latest .

# 运行容器
docker run -d \
  --name dispatch-prediction \
  -p 8000:8000 \
  --env-file .env.local \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/assets:/app/assets \
  dispatch-prediction:latest
```

**5.2 使用Kubernetes部署**

创建 `k8s/deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dispatch-prediction
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dispatch-prediction
  template:
    metadata:
      labels:
        app: dispatch-prediction
    spec:
      containers:
      - name: app
        image: dispatch-prediction:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: dispatch-config
        - secretRef:
            name: dispatch-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

部署：

```bash
kubectl apply -f k8s/
```

---

## 配置说明

### 核心配置文件

#### 1. agent_llm_config.json

Agent核心配置，定义模型和系统行为：

```json
{
  "config": {
    "model": "doubao-seed-1-8-251228",  // LLM模型ID
    "temperature": 0.3,                  // 输出确定性（0-1）
    "top_p": 0.9,
    "max_completion_tokens": 8000,       // 最大输出token数
    "timeout": 600                       // 超时时间（秒）
  },
  "sp": "系统提示词...",                 // Agent角色定义
  "tools": [...]                         // 可用工具列表
}
```

**参数调优建议**：

- **temperature**: 
  - 0.1-0.3: 精准预测场景
  - 0.3-0.7: 平衡预测与创意
  - 0.7-1.0: 探索性分析场景

- **max_completion_tokens**: 
  - 预测报告: 4000-6000
  - 简要建议: 2000-3000

#### 2. prediction_config.json

预测模型参数配置：

```json
{
  "prediction": {
    "prediction_horizon_days": 7,  // 预测时间范围
    "confidence_level": 0.95       // 置信度阈值
  },
  "factors": {
    "weather_impact": {
      "weight": 0.3,               // 权重（总和=1.0）
      "high_temperature_threshold": 35
    },
    ...
  }
}
```

**权重调优**：

根据本地业务特点调整各因素权重：

- 天气敏感地区：提高weather_impact权重
- 季节性明显：提高seasonal_impact权重
- 设备老化严重：提高equipment_impact权重

#### 3. decision_config.json

决策规则配置：

```json
{
  "staffing_rules": {
    "base_ratio": {
      "dispatches_per_person": 8,  // 人均处理能力
      "faults_per_person": 2
    },
    "constraints": {
      "max_work_hours_per_day": 12,
      "max_consecutive_work_days": 6
    }
  }
}
```

**业务适配**：

根据本地调度能力和劳动法规调整约束条件。

---

## 数据源接入

### 标准接口规范

所有数据源需遵循统一接口规范：

```python
def get_data(params: Dict) -> Dict:
    """
    标准数据获取接口
    
    参数：
    - params: 查询参数字典
    
    返回：
    {
        "success": bool,           # 是否成功
        "data": [...],             # 数据列表
        "metadata": {              # 元数据
            "source": "数据源名称",
            "timestamp": "ISO时间戳",
            "record_count": 数字
        }
    }
    """
    pass
```

### 数据源优先级

当多个数据源提供相同数据时，按优先级选择：

1. 实时API（最高优先级）
2. 本地数据库
3. 配置文件
4. 默认值（最低优先级）

---

## API接口文档

### Agent调用接口

#### 1. 业务量预测

**请求**：

```json
{
  "method": "predict",
  "params": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "prediction_days": 7
  }
}
```

**响应**：

```json
{
  "success": true,
  "prediction": {
    "prediction_summary": {
      "total_predicted_dispatches": 350,
      "total_predicted_faults": 45,
      "peak_day": "2024-02-03",
      "confidence_level": 0.87
    },
    "daily_predictions": [...]
  }
}
```

#### 2. 人员决策

**请求**：

```json
{
  "method": "decide",
  "params": {
    "prediction_result": "{...}",
    "current_staff_count": 10,
    "current_shift_schedule": "标准三班制"
  }
}
```

**响应**：

```json
{
  "success": true,
  "decision": {
    "decision_summary": {
      "total_additional_staff_needed": 3,
      "peak_staffing_date": "2024-02-03"
    },
    "daily_staffing_decisions": [...]
  }
}
```

#### 3. 综合报告

**请求**：

```json
{
  "method": "report",
  "params": {
    "output_format": "markdown"
  }
}
```

**响应**：Markdown格式的综合报告

---

## 运维指南

### 日志管理

日志路径：`/var/log/dispatch_prediction/app.log`

日志级别：
- DEBUG: 调试信息
- INFO: 运行信息
- WARNING: 警告信息
- ERROR: 错误信息

日志轮转：每日归档，保留30天

### 监控指标

关键监控指标：

1. **预测准确率**：实际值 vs 预测值偏差
2. **响应时间**：API平均响应时长
3. **资源使用**：CPU、内存使用率
4. **错误率**：API调用失败比例

### 故障排查

**常见问题**：

1. **LLM调用超时**
   - 检查网络连接
   - 增加timeout配置
   - 检查API配额

2. **数据源连接失败**
   - 验证数据库连接参数
   - 检查API密钥有效性
   - 确认网络访问权限

3. **预测结果异常**
   - 检查输入数据质量
   - 调整预测参数
   - 查看错误日志

### 备份与恢复

**备份策略**：

```bash
# 每日备份配置和数据
tar -czf backup_$(date +%Y%m%d).tar.gz config/ assets/

# 备份数据库
pg_dump dispatch_db > db_backup_$(date +%Y%m%d).sql
```

**恢复流程**：

```bash
# 恢复配置
tar -xzf backup_20240101.tar.gz

# 恢复数据库
psql dispatch_db < db_backup_20240101.sql
```

---

## 技术支持

### 文档资源

- [系统架构文档](./ARCHITECTURE.md)
- [API开发文档](./API_REFERENCE.md)
- [配置参数详解](./CONFIG_REFERENCE.md)

### 问题反馈

如遇到技术问题，请提供以下信息：

1. 错误日志片段
2. 配置文件（脱敏后）
3. 复现步骤
4. 环境信息（Python版本、操作系统等）

---

**版本**: v1.0.0  
**更新日期**: 2024-01-01  
**维护团队**: 配网调度智能化项目组
