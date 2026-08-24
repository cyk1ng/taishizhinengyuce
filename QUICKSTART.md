# 快速开始 - 5 分钟部署指南

## 第一步：准备文件

确保项目根目录有以下文件：

```
projects/
├── instantclient-basic-linux.x64-23.26.3.0.0.zip  ← Oracle 客户端
├── .env                                            ← 环境配置（复制 .env.example）
├── config/agent_llm_config.json                    ← 模型配置
└── deploy.bat                                      ← 部署脚本
```

## 第二步：配置环境

### 2.1 复制配置文件

```powershell
copy .env.example .env
```

### 2.2 编辑 .env 文件

打开 `.env` 文件，根据你的环境修改：

**场景 1：内网 + 本地 Ollama 模型（推荐）**

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
DATABASE_URL=oracle+oracledb://OMSCS1:omscs_oms123@10.111.134.209:1521/?service_name=omscsdb
```

**场景 2：纯测试（假数据，无需数据库）**

```env
SKIP_DB=true
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://host.docker.internal:11434/v1
```

### 2.3 修改模型配置

打开 `config/agent_llm_config.json`，修改模型名称：

```json
{
  "config": {
    "model": "qwen2.5:7b",  ← 改成你使用的模型名称
    ...
  }
}
```

## 第三步：安装 Ollama（如使用本地模型）

### 3.1 下载安装

访问：https://ollama.com/download

### 3.2 拉取模型

```bash
ollama pull qwen2.5:7b
```

### 3.3 启动服务

```bash
ollama serve
```

## 第四步：一键部署

### Windows 用户

```powershell
# 完整部署（构建 + 启动）
.\deploy.bat full

# 或测试模式（假数据）
.\deploy.bat test
```

### Linux/Mac 用户

```bash
chmod +x deploy.sh
./deploy.sh full
```

## 第五步：验证部署

### 5.1 访问系统

打开浏览器访问：http://localhost:5000

### 5.2 测试对话

在聊天框输入：

```
你好，请介绍一下这个系统
```

### 5.3 测试数据查询

```
今天的工作量是多少？
当前值班班组是哪个？
```

## 常见问题

### Q1: 构建失败，提示找不到 Oracle Client

**A:** 确保 `instantclient-basic-linux.x64-23.26.3.0.0.zip` 在项目根目录

### Q2: 模型连接失败

**A:** 
1. 检查 Ollama 是否启动：`curl http://localhost:11434/api/tags`
2. 检查模型名称是否正确：`ollama list`
3. 检查 `config/agent_llm_config.json` 中的模型名称

### Q3: 数据库连接失败

**A:**
1. 检查网络：`ping 10.111.134.209`
2. 检查端口：`telnet 10.111.134.209 1521`
3. 如无需数据库，设置 `SKIP_DB=true`

### Q4: 端口 5000 被占用

**A:** 修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "5002:5000"  # 改为 5002 或其他端口
```

## 运维命令

```powershell
# 查看日志
docker compose logs -f dispatch-app

# 重启服务
docker compose restart dispatch-app

# 停止服务
docker compose down

# 进入容器
docker exec -it dispatch-app bash
```

## 下一步

- 详细文档：查看 `DEPLOYMENT.md`
- 功能说明：查看 `README.md`
- 问题反馈：提供错误日志和配置信息
