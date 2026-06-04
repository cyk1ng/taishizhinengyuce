# 🚀 VSCode 运行教程 - 配网调度业务量智能预测系统

## 📋 目录

1. [环境准备](#1-环境准备)
2. [安装依赖](#2-安装依赖)
3. [配置环境变量](#3-配置环境变量)
4. [启动服务](#4-启动服务)
5. [访问界面](#5-访问界面)
6. [测试功能](#6-测试功能)
7. [常见问题](#7-常见问题)

---

## 1. 环境准备

### 1.1 检查 Python 版本

在 VSCode 中打开终端（快捷键：`` Ctrl + ` ``），执行：

```bash
python --version
```

**要求**：Python 3.10 或以上版本

✅ 如果显示 `Python 3.12.3`，说明环境正常  
❌ 如果提示找不到命令，请先安装 Python

---

## 2. 安装依赖

### 2.1 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 2.2 安装依赖包

```bash
# 安装项目依赖
pip install -r requirements.txt
```

⏳ 等待安装完成（可能需要几分钟）

---

## 3. 配置环境变量

### 3.1 打开 .env 文件

在 VSCode 左侧文件管理器中，找到 `.env` 文件并打开。

如果没有 `.env` 文件，请复制 `.env.example`：

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Mac/Linux
cp .env.example .env
```

### 3.2 填写配置信息

打开 `.env` 文件，你会看到：

```env
# 工作空间路径
COZE_WORKSPACE_PATH=F:\Work\WorkSpace\aiWork\projects

# 模型认证配置
COZE_WORKLOAD_IDENTITY_API_KEY=
COZE_INTEGRATION_MODEL_BASE_URL=https://api.coze.cn/v1
```

**需要填写的内容：**

#### ✅ 工作空间路径
将 `COZE_WORKSPACE_PATH` 修改为你的实际项目路径：
- **Windows**: `F:\Work\WorkSpace\aiWork\projects` 或 `D:\projects\aiWork\projects`
- **Mac/Linux**: `/Users/你的用户名/projects/aiWork/projects`

**如何获取路径？**
在 VSCode 终端中执行：
```bash
# Windows
cd

# Mac/Linux
pwd
```

#### ✅ API Key（必填）

**方式1：使用火山引擎（豆包模型）**

1. 访问：https://console.volcengine.com/ark
2. 注册/登录火山引擎账号
3. 开通"方舟"服务
4. 创建推理接入点，选择模型 `doubao-seed-1-8-251228`
5. 复制 API Key

填写到 `.env`：
```env
COZE_WORKLOAD_IDENTITY_API_KEY=你的火山引擎API_Key
COZE_INTEGRATION_MODEL_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

**方式2：使用 Coze 平台**

1. 访问：https://www.coze.cn/
2. 注册/登录 Coze 账号
3. 获取 API Token

填写到 `.env`：
```env
COZE_WORKLOAD_IDENTITY_API_KEY=你的Coze_API_Token
COZE_INTEGRATION_MODEL_BASE_URL=https://api.coze.cn/v1
```

---

## 4. 启动服务

### 4.1 方法1：使用启动脚本（推荐）

#### Windows 用户

**选项A：双击启动**
1. 在 VSCode 左侧文件管理器找到 `start.bat`
2. 右键 → "在集成终端中打开"
3. 或者直接在文件资源管理器中双击 `start.bat`

**选项B：命令行启动**
```bash
# 在 VSCode 终端执行
.\start.bat
```

#### Mac/Linux 用户

```bash
# 添加执行权限（首次需要）
chmod +x start.sh

# 启动服务
./start.sh
```

### 4.2 方法2：手动启动

```bash
# 在 VSCode 终端执行
python src/main.py
```

### 4.3 启动成功标志

看到以下信息表示启动成功：

```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
✅ 前端界面已加载: /workspace/projects/frontend
INFO:     Uvicorn running on http://127.0.0.1:5000 (Press CTRL+C to quit)
```

---

## 5. 访问界面

### 5.1 打开前端界面

在浏览器中访问：

```
http://127.0.0.1:5000
```

或者：

```
http://localhost:5000
```

### 5.2 界面预览

你会看到一个深色主题的专业界面，包含：

- **左侧面板**：快速预测按钮、系统状态
- **中间区域**：智能对话窗口
- **右侧面板**：预测趋势图、人员建议、风险预警

---

## 6. 测试功能

### 6.1 快速测试

点击左侧的"未来7天预测"按钮，观察：
- 对话窗口显示预测过程
- 右侧显示预测趋势图
- 人员建议卡片更新

### 6.2 对话测试

在输入框输入：

```
预测未来7天的调度业务量，并提供人员配置建议
```

按 `Enter` 发送，观察流式响应效果。

### 6.3 API 测试

打开新的终端窗口，测试 API：

```bash
# 健康检查
curl http://127.0.0.1:5000/health

# 发送预测请求
curl -X POST "http://127.0.0.1:5000/stream_run" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"预测未来7天业务量\"}"
```

---

## 7. 常见问题

### ❓ 问题1：端口被占用

**错误信息**：
```
OSError: [Errno 98] Address already in use
```

**解决方法**：
```bash
# Windows：查找并终止占用进程
netstat -ano | findstr :5000
taskkill /PID <进程ID> /F

# Mac/Linux
lsof -i :5000
kill -9 <PID>
```

或者修改端口：
```bash
python src/main.py --port 5001
```

---

### ❓ 问题2：缺少 API Key

**错误信息**：
```
❌ 缺少必要的环境变量: COZE_WORKLOAD_IDENTITY_API_KEY
```

**解决方法**：
1. 确认 `.env` 文件在项目根目录
2. 确认已填写 `COZE_WORKLOAD_IDENTITY_API_KEY` 的值
3. 重启服务

---

### ❓ 问题3：模块未找到

**错误信息**：
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方法**：
```bash
# 确认已激活虚拟环境
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

---

### ❓ 问题4：前端界面无法访问

**可能原因**：
1. 服务未启动
2. 端口被防火墙阻止
3. 浏览器缓存问题

**解决方法**：
1. 确认终端显示 "Uvicorn running on http://127.0.0.1:5000"
2. 尝试使用 `http://localhost:5000`
3. 清除浏览器缓存或使用无痕模式

---

### ❓ 问题5：预测无响应

**可能原因**：
1. API Key 无效
2. 网络连接问题
3. 模型服务异常

**解决方法**：
1. 检查 API Key 是否正确
2. 检查网络连接
3. 查看终端日志错误信息

---

## 📝 快速检查清单

在运行前，请确认：

- [ ] Python 版本 ≥ 3.10
- [ ] 已安装依赖 `pip install -r requirements.txt`
- [ ] `.env` 文件在项目根目录
- [ ] `COZE_WORKSPACE_PATH` 已填写正确路径
- [ ] `COZE_WORKLOAD_IDENTITY_API_KEY` 已填写有效 API Key
- [ ] 端口 5000 未被占用

---

## 🎯 下一步

成功运行后，你可以：

1. **查看 API 文档**：访问 http://127.0.0.1:5000/docs
2. **自定义工具**：修改 `src/tools/` 下的工具代码
3. **调整模型配置**：编辑 `config/agent_llm_config.json`
4. **优化 Prompt**：修改 `config/agent_llm_config.json` 中的 `sp` 字段

---

## 💡 提示

- 首次运行建议使用启动脚本（`start.bat` 或 `start.sh`）
- 开发时建议使用虚拟环境，避免污染系统 Python 环境
- 遇到问题先查看终端日志，通常会有明确的错误提示
- 可以使用 `Ctrl+C` 停止服务

---

**祝你使用愉快！🎉**
