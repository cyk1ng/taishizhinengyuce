# 🎯 从下载到运行 - 完整教程

## 📌 您当前的状态

您已下载：`project_20260317_105404.tar.gz`（智能体项目压缩包）

---

## 第一步：解压项目文件

### Windows系统

1. **右键点击** `project_20260317_105404.tar.gz`
2. 选择 **"解压到当前文件夹"** 或 **"解压到 project_20260317_105404"**
3. 推荐工具：7-Zip、WinRAR、Bandizip

### Mac系统

```bash
# 双击文件自动解压
# 或在终端执行：
tar -xzf project_20260317_105404.tar.gz
```

### Linux系统

```bash
tar -xzf project_20260317_105404.tar.gz
cd project_20260317_105404
```

**✅ 解压后目录结构：**
```
project_20260317_105404/
├── src/              # 源代码
├── config/           # 配置文件
├── assets/           # 资源文件
├── scripts/          # 启动脚本
├── requirements.txt  # 依赖列表
└── README.md
```

---

## 第二步：安装Python环境

### 检查是否已安装Python

打开终端/命令行，执行：

```bash
python --version
# 或
python3 --version
```

**期望输出**：`Python 3.10.x` 或更高版本

### 如果没有安装Python

**Windows**：
1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.10+ 版本
3. 安装时勾选 **"Add Python to PATH"**

**Mac**：
```bash
brew install python@3.10
```

**Linux (Ubuntu)**：
```bash
sudo apt update
sudo apt install python3.10 python3-pip
```

---

## 第三步：安装项目依赖

### 进入项目目录

```bash
cd project_20260317_105404
```

### 安装依赖包

```bash
pip install -r requirements.txt
```

**如果速度慢，使用国内镜像：**
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**✅ 安装完成标志：**
```
Successfully installed langchain-1.0.3 langgraph-1.0.2 ...
```

---

## 第四步：配置API密钥（关键！）

### 方式1：创建.env文件（推荐）

在项目根目录创建 `.env` 文件：

```bash
# Windows (记事本)
notepad .env

# Mac/Linux
nano .env
```

**写入以下内容：**
```env
# 必需：LLM API配置
COZE_WORKLOAD_IDENTITY_API_KEY=your_actual_api_key_here
COZE_INTEGRATION_MODEL_BASE_URL=https://api.coze.cn
```

> ⚠️ **重要**：将 `your_actual_api_key_here` 替换为您的真实API密钥

### 方式2：环境变量（临时）

**Windows (PowerShell)：**
```powershell
$env:COZE_WORKLOAD_IDENTITY_API_KEY="your_api_key"
$env:COZE_INTEGRATION_MODEL_BASE_URL="https://api.coze.cn"
```

**Mac/Linux：**
```bash
export COZE_WORKLOAD_IDENTITY_API_KEY="your_api_key"
export COZE_INTEGRATION_MODEL_BASE_URL="https://api.coze.cn"
```

---

## 第五步：运行智能体

### ✅ 验证安装

```bash
python -c "from agents.agent import build_agent; print('✅ 环境就绪')"
```

**期望输出**：`✅ 环境就绪`

### 🚀 启动智能体

**方式1：交互模式**
```bash
python src/main.py
```

**方式2：快速测试**
```python
python -c "
from agents.agent import build_agent

agent = build_agent()
response = agent.invoke({
    'messages': [{'role': 'user', 'content': '预测未来7天业务量'}]
})

print(response['messages'][-1].content)
"
```

---

## 第六步：使用智能体

### 示例请求

```python
from agents.agent import build_agent

# 构建智能体
agent = build_agent()

# 发送请求
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "请预测未来7天的配网调度业务量，并给出人员调整建议"}
    ]
})

# 获取响应
print(result["messages"][-1].content)
```

### 预期输出

```
# 配网调度业务量智能预测与人员调整决策报告

## 一、业务量预测摘要
- 预测总调度次数: 321
- 预测总故障数: 71
- 峰值日期: 2026-03-18
...

## 三、人员调整决策
- 需增补人员总数: 2
- 峰值人员数: 12
...
```

---

## 🐛 常见问题解决

### ❌ 问题1：找不到模块

```
ModuleNotFoundError: No module named 'langchain'
```

**解决方案**：
```bash
pip install langchain==1.0.3 langgraph==1.0.2
```

### ❌ 问题2：API密钥错误

```
Error: Invalid API key
```

**解决方案**：
1. 检查 `.env` 文件是否存在
2. 确认API密钥格式正确（无引号、无空格）
3. 重启终端/命令行窗口

### ❌ 问题3：端口被占用

```
OSError: [Errno 98] Address already in use
```

**解决方案**：
```bash
# 查找占用端口的进程
lsof -i:8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# 使用其他端口
python src/main.py --port 8001
```

### ❌ 问题4：Python版本不兼容

```
SyntaxError: invalid syntax
```

**解决方案**：
```bash
# 确认Python版本 >= 3.10
python --version

# 如果版本过低，升级Python
# 或使用 python3.10 显式指定版本
python3.10 src/main.py
```

---

## 📞 需要帮助？

如果遇到问题，请提供：

1. **错误信息截图**
2. **Python版本**：`python --version`
3. **操作系统版本**
4. **依赖安装日志**

---

## 🎉 成功运行标志

看到以下输出表示成功：

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

访问 `http://localhost:8000` 即可使用智能体！
