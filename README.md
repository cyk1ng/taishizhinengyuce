# 配网调度业务量智能预测系统

基于多源数据融合和人工智能技术的配网调度业务量智能预测与决策支持系统。

## 系统功能

### 核心功能
- **数据融合分析**：整合历史调度记录、天气数据、节假日信息、设备状态等多源数据
- **业务量预测**：基于多因素分析预测未来调度业务量趋势（支持 LLM 和时序模型）
- **人员决策支持**：生成科学的值班人员调整建议，优化人员配置
- **智能排班**：基于业务量预测和人员信息，生成科学合理的排班方案
- **工作量统计**：实时统计计划任务和非计划任务工作量
- **风险预警**：识别业务量异常和潜在风险，提供预警和建议
- **智能问答**：通过 AI 对话界面，自然语言查询和分析数据

### 技术栈
- **后端**：Python + FastAPI + LangChain + LangGraph
- **前端**：HTML + CSS + JavaScript + Chart.js
- **数据库**：Oracle 11g+
- **AI 模型**：支持 Ollama 本地模型 / 火山引擎云端模型
- **部署**：Docker 容器化

## 快速开始

### 1. 准备环境

```bash
# 克隆项目
git clone <repository-url>
cd projects

# 复制环境配置
cp .env.example .env
```

### 2. 配置环境

编辑 `.env` 文件，根据你的环境修改配置：

**内网部署（推荐）：**
```env
# 本地 Ollama 模型
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://host.docker.internal:11434/v1

# Oracle 数据库
DB_TYPE=oracle
DB_HOST=10.111.134.209
DB_PORT=1521
DB_NAME=omscsdb
DB_USER=OMSCS1
DB_PASSWORD=omscs_oms123
```

**测试模式（假数据）：**
```env
SKIP_DB=true
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://host.docker.internal:11434/v1
```

### 3. 安装 Ollama（如使用本地模型）

```bash
# 下载安装
# https://ollama.com/download

# 拉取模型
ollama pull qwen2.5:7b

# 启动服务
ollama serve
```

### 4. 一键部署

**Windows:**
```powershell
.\deploy.bat full
```

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh full
```

### 5. 访问系统

打开浏览器访问：http://localhost:5000

## 文档

- **快速开始**：[QUICKSTART.md](QUICKSTART.md) - 5 分钟部署指南
- **详细部署**：[DEPLOYMENT.md](DEPLOYMENT.md) - 完整部署文档
- **检查清单**：[CHECKLIST.md](CHECKLIST.md) - 部署前检查项

## 项目结构

```
projects/
├── src/                    # 后端源码
│   ├── agents/            # Agent 定义
│   ├── tools/             # 工具函数
│   ├── storage/           # 数据库连接
│   ── main.py            # FastAPI 主程序
├── frontend/              # 前端代码
│   ├── index.html         # 主页面
│   ├── css/               # 样式文件
│   └── js/                # JavaScript 文件
├── config/                # 配置文件
│   └── agent_llm_config.json  # 模型配置
├── assets/                # 资源文件
├── .env.example           # 环境变量模板
├── docker-compose.yml     # Docker 编排
├── Dockerfile             # Docker 镜像
├── deploy.sh              # Linux 部署脚本
├── deploy.bat             # Windows 部署脚本
└── README.md              # 本文件
```

## 常用命令

```bash
# 构建镜像
docker compose build dispatch-app

# 启动服务
docker compose up -d dispatch-app

# 查看日志
docker compose logs -f dispatch-app

# 重启服务
docker compose restart dispatch-app

# 停止服务
docker compose down

# 进入容器
docker exec -it dispatch-app bash
```

## 智能问答示例

### 数据查询
```
今天的工作量是多少？
当前值班班组是哪个？
明天的天气怎么样？
```

### 预测分析
```
预测明天的工作量
分析下周的人员需求
哪些时段可能超负荷？
```

### 排班管理
```
生成下周的排班方案
分析当前排班的公平性
建议增加哪些人员？
```

### 风险预警
```
当前有哪些风险？
如何避免业务量超负荷？
设备状态如何？
```

## 数据库表说明

| 表名 | 用途 |
|------|------|
| OC_SCHEDULE_TEAM | 班组信息 |
| OC_SCHEDULE_RECORD | 排班记录 |
| OC_SCHEDULE_PERSON | 人员信息 |
| OC_DISPATCH_WORK_ORDER | 工作票 |
| OC_FAULT_LOG | 故障日志 |
| OC_DEFECT_RECORD | 缺陷记录 |
| OC_OVERLOAD_RECORD | 重过载记录 |

## 模型配置

### 支持的模型

| 模型服务 | 模型名称 | 内存需求 |
|---------|---------|---------|
| Ollama | `qwen2.5:7b` | 8GB |
| Ollama | `qwen2.5:14b` | 16GB |
| Ollama | `llama3:8b` | 8GB |
| 火山引擎 | `doubao-seed-1-8-251228` | 云端 |
| vLLM | `Qwen/Qwen2.5-7B-Instruct` | 16GB |

### 修改模型

编辑 `config/agent_llm_config.json`：

```json
{
  "config": {
    "model": "qwen2.5:7b",  // 修改为你的模型名称
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 8000,
    "timeout": 600
  }
}
```

## 常见问题

### Q: 数据库连接失败？
A: 检查网络连通性，确认 Oracle Instant Client 已正确安装。

### Q: 模型响应慢？
A: 本地模型响应速度取决于硬件，建议使用 7B 模型 + 8GB 内存。

### Q: 天气数据无法获取？
A: 内网环境可能无法访问外网 API，系统会自动使用假数据。

### Q: 如何更新部署？
A: 拉取最新代码后，执行 `docker compose build` 重新构建。

## 技术支持

如遇到问题，请提供：
1. 错误日志（`docker compose logs`）
2. 操作系统和 Docker 版本
3. 配置文件内容（脱敏后）

## 许可证

内部使用，未经授权禁止外传。
