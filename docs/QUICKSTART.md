# 🚀 智能体运行指南

## 快速开始（3步启动）

### 步骤1：安装依赖

```bash
cd /workspace/projects
pip install -r requirements.txt
```

### 步骤2：配置环境变量

创建 `.env` 文件：

```bash
# 必需：LLM API配置
COZE_WORKLOAD_IDENTITY_API_KEY=your_api_key_here
COZE_INTEGRATION_MODEL_BASE_URL=https://api.coze.cn

# 可选：数据库配置（如需使用真实数据）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dispatch_db
DB_USER=postgres
DB_PASSWORD=password

# 可选：天气API
WEATHER_API_ENDPOINT=https://api.weather.com
WEATHER_API_KEY=your_weather_key
```

### 步骤3：启动智能体

**方式1：命令行交互模式**
```bash
python src/main.py
```

**方式2：HTTP服务模式**
```bash
bash scripts/local_run.sh
```

**方式3：测试运行**
```python
# 测试脚本
from agents.agent import build_agent

agent = build_agent()
response = agent.invoke({
    "messages": [
        {"role": "user", "content": "预测未来7天的配网调度业务量"}
    ]
})
print(response)
```

---

## 详细运行方式

### 1️⃣ 本地开发环境运行

#### 1.1 环境准备

```bash
# 检查Python版本（需要3.10+）
python --version

# 安装依赖
pip install -r requirements.txt

# 验证安装
python -c "from agents.agent import build_agent; print('✅ 环境就绪')"
```

#### 1.2 配置文件检查

确保以下配置文件存在：

```
config/
├── agent_llm_config.json       ✅ Agent核心配置
assets/
├── data_sources.json           ✅ 数据源配置
├── prediction_config.json      ✅ 预测参数
├── decision_config.json        ✅ 决策规则
└── holiday_calendar.json       ✅ 节假日数据
```

#### 1.3 启动服务

```bash
# 进入项目目录
cd /workspace/projects

# 启动主服务
python src/main.py
```

访问：`http://localhost:8000`

---

### 2️⃣ Docker容器运行

#### 2.1 构建镜像

```bash
# 创建Dockerfile（如果不存在）
cat > Dockerfile << 'EOF'
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "src/main.py"]
EOF

# 构建镜像
docker build -t dispatch-prediction:latest .
```

#### 2.2 运行容器

```bash
docker run -d \
  --name dispatch-agent \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/assets:/app/assets \
  dispatch-prediction:latest
```

#### 2.3 查看日志

```bash
docker logs -f dispatch-agent
```

---

### 3️⃣ API调用方式

#### 3.1 HTTP接口调用

**启动服务后，使用以下API：**

```bash
# 预测业务量
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "prediction_days": 7
  }'

# 获取人员决策
curl -X POST http://localhost:8000/api/decision \
  -H "Content-Type: application/json" \
  -d '{
    "prediction_result": "{...}",
    "current_staff_count": 10
  }'

# 生成报告
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d '{
    "output_format": "markdown"
  }'
```

#### 3.2 Python SDK调用

```python
from agents.agent import build_agent

# 构建Agent
agent = build_agent()

# 发送请求
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "请预测未来7天业务量并给出人员建议"}
    ]
})

# 获取响应
response = result["messages"][-1].content
print(response)
```

---

### 4️⃣ 集成到现有系统

#### 4.1 作为微服务集成

```python
# app.py
from fastapi import FastAPI
from agents.agent import build_agent

app = FastAPI()
agent = build_agent()

@app.post("/api/predict")
async def predict_dispatch(request: dict):
    """业务量预测接口"""
    response = agent.invoke({
        "messages": [
            {"role": "user", "content": f"预测未来{request.get('days', 7)}天业务量"}
        ]
    })
    return {"result": response["messages"][-1].content}

@app.post("/api/decision")
async def make_decision(request: dict):
    """人员决策接口"""
    response = agent.invoke({
        "messages": [
            {"role": "user", "content": f"基于预测结果生成人员决策: {request}"}
        ]
    })
    return {"decision": response["messages"][-1].content}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 4.2 定时任务集成

```python
# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agents.agent import build_agent

scheduler = AsyncIOScheduler()
agent = build_agent()

async def daily_prediction():
    """每日定时预测任务"""
    result = agent.invoke({
        "messages": [{"role": "user", "content": "预测未来7天业务量"}]
    })
    # 发送结果到邮件/飞书/企业微信
    send_notification(result)

# 每天早上8点执行
scheduler.add_job(daily_prediction, 'cron', hour=8, minute=0)
scheduler.start()
```

---

## 常见问题排查

### ❌ 问题1：依赖安装失败

```bash
# 解决方案：使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### ❌ 问题2：API密钥无效

```bash
# 检查环境变量
echo $COZE_WORKLOAD_IDENTITY_API_KEY

# 如果为空，设置环境变量
export COZE_WORKLOAD_IDENTITY_API_KEY="your_key_here"
```

### ❌ 问题3：端口被占用

```bash
# 查找占用端口的进程
lsof -i:8000

# 杀死进程
kill -9 <PID>

# 或使用其他端口
python src/main.py --port 8001
```

### ❌ 问题4：预测结果异常

```bash
# 检查日志
tail -f /app/work/logs/bypass/app.log

# 验证数据源
python -c "
from tools.data_fusion import get_historical_dispatch_data
result = get_historical_dispatch_data.invoke({
    'start_date': '2024-01-01',
    'end_date': '2024-01-31'
})
print(result)
"
```

---

## 性能优化建议

### 1. 启用缓存

```python
# 在.env中添加
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
```

### 2. 并发处理

```bash
# 使用多进程启动
uvicorn src.main:app --workers 4 --host 0.0.0.0 --port 8000
```

### 3. 数据库连接池

```python
# 优化数据库连接
import psycopg2.pool

connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
```

---

## 下一步

1. ✅ 按照上述步骤启动智能体
2. 📝 根据本地业务调整配置文件
3. 🔌 接入真实数据源（替换示例数据）
4. 🎯 集成到您的业务系统

详细移植指南：`docs/DEPLOYMENT.md`  
系统架构文档：`docs/ARCHITECTURE.md`
