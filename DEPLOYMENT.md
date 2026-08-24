# 配网调度业务量智能预测系统 - 内网部署指南

## 一、部署前准备

### 1.1 环境要求

| 组件 | 要求 | 说明 |
|------|------|------|
| Docker | 20.10+ | 容器化运行环境 |
| Oracle Instant Client | 23.26 | 已包含在项目根目录 |
| 数据库 | Oracle 11g+ | 内网 Oracle 数据库 |
| 大模型 | Ollama/云端 | 智能问答核心 |

### 1.2 网络要求

```
内网服务器 → Oracle 数据库 (10.111.134.209:1521)
内网服务器 → 大模型服务 (本地或云端)
用户浏览器 → 内网服务器 (5000 端口)
```

---

## 二、配置步骤

### 2.1 复制配置文件

```bash
# 复制环境变量配置模板
cp .env.example .env
```

### 2.2 编辑 .env 文件

根据你的内网环境，修改以下配置：

#### 方案 A：使用本地 Ollama 模型（推荐，无需外网）

```env
# 模型配置 - 本地 Ollama
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://host.docker.internal:11434/v1

# 数据库配置 - Oracle
DB_TYPE=oracle
DB_HOST=10.111.134.209
DB_PORT=1521
DB_NAME=omscsdb
DB_USER=OMSCS1
DB_PASSWORD=omscs_oms123
DATABASE_URL=oracle+oracledb://OMSCS1:omscs_oms123@10.111.134.209:1521/?service_name=omscsdb

# 天气 API（需要外网，如内网无外网可跳过）
WEATHER_API_KEY=44ff4071f86641979f59da2daed5505e
WEATHER_API_ENDPOINT=https://devapi.qweather.com/v7
DEFAULT_CITY=101280101
```

#### 方案 B：使用云端模型（需要外网访问）

```env
# 模型配置 - 火山引擎
COZE_WORKLOAD_IDENTITY_API_KEY=你的火山引擎 API_KEY
COZE_INTEGRATION_MODEL_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 数据库配置 - Oracle（同上）
DB_TYPE=oracle
DB_HOST=10.111.134.209
DB_PORT=1521
DB_NAME=omscsdb
DB_USER=OMSCS1
DB_PASSWORD=omscs_oms123
DATABASE_URL=oracle+oracledb://OMSCS1:omscs_oms123@10.111.134.209:1521/?service_name=omscsdb
```

#### 方案 C：纯测试模式（无需数据库，用假数据）

```env
# 跳过数据库
SKIP_DB=true

# 模型配置
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://host.docker.internal:11434/v1
```

### 2.3 修改模型配置文件

编辑 `config/agent_llm_config.json`，确保模型名称正确：

```json
{
  "config": {
    "model": "qwen2.5:7b",  // Ollama 模型名称
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 8000,
    "timeout": 600,
    "thinking": "disabled"
  },
  "sp": "...",
  "tools": [...]
}
```

**常用模型名称对照：**

| 模型服务 | 模型名称 |
|---------|---------|
| Ollama | `qwen2.5:7b`, `llama3:8b`, `glm4:9b` |
| 火山引擎 | `doubao-seed-1-8-251228` |
| vLLM | `Qwen/Qwen2.5-7B-Instruct` |

---

## 三、部署步骤

### 3.1 构建 Docker 镜像

```bash
# 进入项目目录
cd /path/to/projects

# 构建镜像
docker compose build dispatch-app
```

### 3.2 启动服务

```bash
# 启动生产模式（连接数据库）
docker compose up -d dispatch-app

# 或启动测试模式（假数据）
docker compose up -d dispatch-app-test
```

### 3.3 查看日志

```bash
# 查看启动日志
docker compose logs -f dispatch-app

# 看到以下信息表示启动成功：
# INFO:     Uvicorn running on http://0.0.0.0:5000
```

### 3.4 访问系统

- 生产模式：http://服务器IP:5000
- 测试模式：http://服务器IP:5001

---

## 四、Ollama 本地模型部署（推荐）

### 4.1 安装 Ollama

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
下载 https://ollama.com/download/OllamaSetup.exe

### 4.2 拉取模型

```bash
# 推荐模型（7B 参数，8GB 内存即可运行）
ollama pull qwen2.5:7b

# 或更大的模型（需要更多内存）
ollama pull qwen2.5:14b
ollama pull llama3:8b
```

### 4.3 启动 Ollama 服务

```bash
# 后台运行
ollama serve &

# 验证服务
curl http://localhost:11434/api/tags
```

### 4.4 Docker 内访问宿主机 Ollama

在 `docker-compose.yml` 中已配置：
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

容器内通过 `http://host.docker.internal:11434/v1` 访问宿主机 Ollama。

---

## 五、数据库连接配置

### 5.1 Oracle 数据库连接信息

```
主机：10.111.134.209
端口：1521
服务名：omscsdb
用户：OMSCS1
密码：omscs_oms123
```

### 5.2 验证数据库连接

```bash
# 进入容器
docker exec -it dispatch-app bash

# 测试连接
python -c "
import oracledb
conn = oracledb.connect(
    user='OMSCS1',
    password='omscs_oms123',
    dsn='10.111.134.209:1521/omscsdb'
)
print('连接成功！')
conn.close()
"
```

### 5.3 数据库表说明

| 表名 | 用途 |
|------|------|
| OC_SCHEDULE_TEAM | 班组信息 |
| OC_SCHEDULE_RECORD | 排班记录 |
| OC_SCHEDULE_PERSON | 人员信息 |
| OC_DISPATCH_WORK_ORDER | 工作票 |
| OC_FAULT_LOG | 故障日志 |
| OC_DEFECT_RECORD | 缺陷记录 |
| OC_OVERLOAD_RECORD | 重过载记录 |

---

## 六、智能问答测试

### 6.1 测试对话功能

访问系统后，在聊天框输入：

```
你好，请介绍一下这个系统的功能
```

### 6.2 测试数据查询

```
今天的工作量是多少？
当前值班班组是哪个？
明天的天气怎么样？
```

### 6.3 测试预测功能

```
预测明天的工作量
分析下周的人员需求
```

### 6.4 测试排班功能

```
生成下周的排班方案
分析当前排班的公平性
```

---

## 七、常见问题

### 7.1 数据库连接失败

**问题：** `OracleDB 连接失败`

**解决：**
1. 检查网络：`ping 10.111.134.209`
2. 检查端口：`telnet 10.111.134.209 1521`
3. 检查用户名密码是否正确
4. 检查 Oracle Instant Client 版本是否匹配

### 7.2 模型连接失败

**问题：** `LLM 调用失败`

**解决：**
1. 检查 Ollama 服务是否启动：`curl http://localhost:11434/api/tags`
2. 检查模型是否已拉取：`ollama list`
3. 检查 `config/agent_llm_config.json` 中的模型名称是否正确
4. Docker 内访问宿主机：确保 `extra_hosts` 配置正确

### 7.3 天气 API 不可用

**问题：** 内网无法访问外网天气 API

**解决：**
1. 使用假数据模式：设置 `SKIP_DB=true`
2. 或配置内网代理访问外网
3. 或手动输入天气数据

### 7.4 端口冲突

**问题：** `port is already allocated`

**解决：**
```bash
# 修改 docker-compose.yml 中的端口映射
ports:
  - "5002:5000"  # 改为其他端口
```

---

## 八、运维命令

### 8.1 服务管理

```bash
# 启动服务
docker compose up -d dispatch-app

# 停止服务
docker compose down

# 重启服务
docker compose restart dispatch-app

# 查看状态
docker compose ps
```

### 8.2 日志查看

```bash
# 实时日志
docker compose logs -f dispatch-app

# 最近 100 行日志
docker compose logs --tail=100 dispatch-app
```

### 8.3 进入容器

```bash
docker exec -it dispatch-app bash
```

### 8.4 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建
docker compose build dispatch-app

# 重启服务
docker compose up -d dispatch-app
```

---

## 九、性能优化建议

### 9.1 模型选择

| 场景 | 推荐模型 | 内存需求 |
|------|---------|---------|
| 快速响应 | qwen2.5:7b | 8GB |
| 复杂分析 | qwen2.5:14b | 16GB |
| 高精度 | qwen2.5:32b | 32GB |

### 9.2 数据库优化

- 确保 Oracle 数据库索引完整
- 定期清理历史数据
- 使用连接池减少连接开销

### 9.3 网络优化

- 内网部署减少网络延迟
- 使用本地模型避免外网依赖
- 配置 CDN 加速静态资源

---

## 十、联系支持

如遇到部署问题，请提供以下信息：

1. 操作系统版本
2. Docker 版本
3. 错误日志（`docker compose logs`）
4. 网络连通性测试结果
