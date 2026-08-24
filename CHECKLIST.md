# 内网部署检查清单

## 部署前检查

### 1. 文件准备

- [ ] Oracle Instant Client 文件已下载
  - 文件名：`instantclient-basic-linux.x64-23.26.3.0.0.zip`
  - 位置：项目根目录
  - 下载：https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html

- [ ] Docker Desktop 已安装并启动
  - 版本：20.10+
  - 状态：托盘图标显示 "Docker Desktop is running"

- [ ] 项目代码已拉取
  ```powershell
  git pull
  ```

### 2. 环境配置

- [ ] `.env` 文件已创建
  ```powershell
  copy .env.example .env
  ```

- [ ] 模型配置已修改
  - 文件：`config/agent_llm_config.json`
  - 字段：`config.model`
  - 示例：`qwen2.5:7b`（Ollama）或 `doubao-seed-1-8-251228`（火山引擎）

- [ ] 数据库配置已修改（如需要）
  - 文件：`.env`
  - 字段：`DB_HOST`, `DB_USER`, `DB_PASSWORD` 等

### 3. 模型服务

#### 使用本地 Ollama

- [ ] Ollama 已安装
  - 下载：https://ollama.com/download
  - 验证：`ollama --version`

- [ ] 模型已拉取
  ```bash
  ollama pull qwen2.5:7b
  ollama list  # 验证
  ```

- [ ] Ollama 服务已启动
  ```bash
  ollama serve
  curl http://localhost:11434/api/tags  # 验证
  ```

#### 使用云端模型

- [ ] API Key 已获取
- [ ] `.env` 中已配置 API Key 和 Base URL
- [ ] 网络可访问云端服务

### 4. 数据库连接（生产模式）

- [ ] 网络连通
  ```powershell
  ping 10.111.134.209
  telnet 10.111.134.209 1521
  ```

- [ ] 数据库账号密码正确
  - 用户：OMSCS1
  - 密码：omscs_oms123
  - 服务名：omscsdb

- [ ] 数据库表存在
  - OC_SCHEDULE_TEAM
  - OC_SCHEDULE_RECORD
  - OC_DISPATCH_WORK_ORDER
  - 等...

### 5. 端口检查

- [ ] 端口 5000 未被占用
  ```powershell
  netstat -ano | findstr :5000
  ```

- [ ] 如被占用，修改 `docker-compose.yml` 端口映射

---

## 部署中检查

### 6. 构建镜像

```powershell
docker compose build dispatch-app
```

检查项：
- [ ] 构建成功，无错误
- [ ] 镜像大小合理（约 1-2GB）

### 7. 启动服务

```powershell
docker compose up -d dispatch-app
```

检查项：
- [ ] 容器启动成功
  ```powershell
  docker ps | findstr dispatch-app
  ```

- [ ] 日志无严重错误
  ```powershell
  docker compose logs dispatch-app
  ```

### 8. 访问验证

- [ ] 浏览器可访问 http://localhost:5000
- [ ] 页面正常加载
- [ ] 图表正常显示

---

## 部署后验证

### 9. 功能测试

#### 9.1 对话功能

- [ ] 发送 "你好" 有回复
- [ ] 回复内容合理，无乱码

#### 9.2 数据查询

- [ ] 发送 "今天的工作量" 有数据返回
- [ ] 数据与数据库一致（生产模式）

#### 9.3 预测功能

- [ ] 发送 "预测明天工作量" 有预测结果
- [ ] 预测结果包含置信度

#### 9.4 排班功能

- [ ] 发送 "生成排班方案" 有排班结果
- [ ] 排班符合规则

### 10. 性能检查

- [ ] 响应时间 < 30 秒（首次可能较慢）
- [ ] 无内存泄漏
- [ ] 日志无频繁错误

---

## 问题记录

如遇到问题，记录以下信息：

| 项目 | 内容 |
|------|------|
| 问题描述 | |
| 错误日志 | |
| 操作系统 | |
| Docker 版本 | |
| 模型配置 | |
| 数据库配置 | |
| 网络环境 | |

---

## 快速命令参考

```powershell
# 构建
docker compose build dispatch-app

# 启动
docker compose up -d dispatch-app

# 日志
docker compose logs -f dispatch-app

# 重启
docker compose restart dispatch-app

# 停止
docker compose down

# 进入容器
docker exec -it dispatch-app bash

# 测试数据库连接
docker exec -it dispatch-app python -c "
import oracledb
conn = oracledb.connect(user='OMSCS1', password='omscs_oms123', dsn='10.111.134.209:1521/omscsdb')
print('连接成功！')
conn.close()
"
```

---

## 签字确认

| 角色 | 姓名 | 日期 | 签字 |
|------|------|------|------|
| 部署人员 | | | |
| 测试人员 | | | |
| 运维人员 | | | |
