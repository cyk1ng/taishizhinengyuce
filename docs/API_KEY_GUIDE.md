# 🔑 API密钥获取完整指南

## 问题：我没有API密钥怎么办？

---

## 方案一：使用Coze平台（推荐）⭐

### Step 1: 注册Coze账号

1. 访问：**https://www.coze.cn**
2. 点击右上角 **"登录/注册"**
3. 可选择：
   - 手机号注册
   - 微信扫码登录
   - 抖音账号登录

### Step 2: 创建工作空间

1. 登录后，进入 **"工作空间"**
2. 点击 **"创建工作空间"**
3. 输入名称（如：配网调度预测）
4. 选择 **"个人版"**（免费）

### Step 3: 获取API密钥

1. 进入工作空间
2. 点击左侧菜单 **"API密钥管理"**
3. 点击 **"创建新密钥"**
4. 复制生成的密钥（只显示一次，请妥善保存）

**API密钥格式示例**：
```
pat-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 4: 配置项目

在项目根目录创建 `.env` 文件：

```env
COZE_WORKLOAD_IDENTITY_API_KEY=pat-你的密钥
COZE_INTEGRATION_MODEL_BASE_URL=https://api.coze.cn
```

---

## 方案二：使用其他LLM平台

### 选项A：豆包大模型（字节跳动）

1. 访问：https://www.volcengine.com/product/doubao
2. 注册账号 → 控制台 → API密钥管理
3. 修改配置文件 `config/agent_llm_config.json`：
```json
{
  "config": {
    "model": "doubao-seed-1-8-251228",
    ...
  }
}
```

### 选项B：DeepSeek

1. 访问：https://platform.deepseek.com
2. 注册并创建API Key
3. 修改配置：
```json
{
  "config": {
    "model": "deepseek-v3-2-251201",
    ...
  }
}
```

### 选项C：OpenAI（需国际网络）

1. 访问：https://platform.openai.com/api-keys
2. 创建API Key
3. 修改 `.env`：
```env
OPENAI_API_KEY=sk-xxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## 方案三：本地模型（无需API密钥）

如果您有GPU显卡，可以使用本地模型：

### 安装Ollama

```bash
# Mac/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# 访问 https://ollama.com/download 下载安装
```

### 下载模型

```bash
ollama pull qwen2:7b
```

### 修改Agent代码

编辑 `src/agents/agent.py`：

```python
from langchain_community.llms import Ollama

llm = Ollama(
    model="qwen2:7b",
    temperature=0.3
)
```

---

## 🎯 推荐方案对比

| 方案 | 优点 | 缺点 | 成本 |
|------|------|------|------|
| **Coze平台** | 免费额度充足，国内访问快 | 需注册账号 | 免费 |
| **豆包** | 中文能力强 | 需实名认证 | 按量付费 |
| **DeepSeek** | 性价比高 | 新平台 | 按量付费 |
| **本地模型** | 完全免费，数据安全 | 需要GPU | 硬件成本 |

---

## 📝 获取密钥后的配置步骤

### 1. 创建配置文件

在项目根目录创建 `.env` 文件：

```bash
# Windows (PowerShell)
New-Item -Path .env -ItemType File

# Mac/Linux
touch .env
```

### 2. 编辑文件内容

```env
# 方式1：使用记事本/VS Code打开
notepad .env    # Windows
nano .env       # Mac/Linux

# 粘贴以下内容：
COZE_WORKLOAD_IDENTITY_API_KEY=pat-你的密钥
COZE_INTEGRATION_MODEL_BASE_URL=https://api.coze.cn
```

### 3. 验证配置

```bash
python -c "import os; print('API Key:', os.getenv('COZE_WORKLOAD_IDENTITY_API_KEY')[:10] + '...')"
```

**✅ 期望输出**：`API Key: pat-xxxxxx...`

---

## 🆘 常见问题

### Q1: Coze平台免费吗？
**A**: Coze个人版提供免费额度，足够测试和轻度使用。

### Q2: API密钥忘记了怎么办？
**A**: 登录Coze平台 → API密钥管理 → 查看或重新生成。

### Q3: 可以用试用版测试吗？
**A**: 可以！先注册Coze账号，获取免费额度测试。

### Q4: 没有GPU能用本地模型吗？
**A**: 可以使用CPU版本，但速度较慢。建议使用云API。

---

## 🚀 快速开始（推荐路径）

1. **注册Coze账号** → https://www.coze.cn （5分钟）
2. **创建工作空间** → 获取API密钥（2分钟）
3. **配置项目** → 创建 `.env` 文件（1分钟）
4. **运行测试** → `python src/main.py`

总计时间：**10分钟内完成** ✅

---

## 📞 需要帮助？

如果您在获取API密钥过程中遇到问题：

1. 截图当前步骤
2. 描述具体问题
3. 告诉我您选择的方案

我会立即协助您解决！
