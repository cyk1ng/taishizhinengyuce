# Ollama启动指南

## 问题诊断
当前状态：❌ Ollama服务未启动

## 解决步骤

### 步骤1：启动Ollama服务

在您的本地电脑上，打开一个新的终端窗口，运行：

```bash
ollama serve
```

**预期输出：**
```
INFO[0000] ollama is running
INFO[0000] routes are registered on /v1/api
INFO[0000] Listening on [::]:11434
```

**保持这个终端窗口运行，不要关闭！**

---

### 步骤2：验证Ollama服务运行正常

在另一个终端窗口，运行：

```bash
curl http://localhost:11434/api/tags
```

或者直接在浏览器访问：
```
http://localhost:11434/api/tags
```

**预期输出：**
```json
{
  "models": [
    {
      "name": "qwen2.5:7b",
      "modified_at": "2024-04-22T08:00:00Z",
      "size": 4735130704,
      "digest": "abc123..."
    }
  ]
}
```

---

### 步骤3：检查模型是否已下载

```bash
ollama list
```

**如果看到以下输出，说明模型已下载：**
```
NAME                     ID              SIZE      MODIFIED
qwen2.5:7b              abc123...       4.4 GB    2 hours ago
```

**如果没有qwen2.5:7b模型，下载它：**
```bash
ollama pull qwen2.5:7b
```

---

### 步骤4：测试模型响应

```bash
ollama run qwen2.5:7b "你好"
```

**预期输出：**
```
你好！我是Qwen，很高兴为您服务。
```

---

### 步骤5：启动项目

**方法1：使用快速启动脚本（推荐）**

在项目目录下运行：

**Windows:**
```bash
scripts\start_with_ollama.bat
```

**Linux/Mac:**
```bash
./scripts/start_with_ollama.sh
```

**方法2：手动启动**

打开两个终端窗口：

**终端1 - 启动后端：**
```bash
cd /workspace/projects
python src/main.py
```

**终端2 - 启动前端：**
```bash
cd /workspace/projects
python -m http.server 8000 --directory frontend
```

然后在浏览器访问：
```
http://localhost:8000
```

---

## 常见问题

### Q1: 提示 "ollama: command not found"
**A:** Ollama未安装，请先安装：

**Windows:**
1. 访问 https://ollama.com/download
2. 下载安装包
3. 运行安装程序

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

---

### Q2: Ollama启动后立即关闭
**A:** 可能是端口被占用。尝试：

**Windows:**
```bash
netstat -ano | findstr :11434
```

**Linux/Mac:**
```bash
lsof -i :11434
```

如果有进程占用，关闭该进程或更换端口。

---

### Q3: 模型下载失败
**A:** 可能是网络问题。尝试：

1. 检查网络连接
2. 使用镜像源
3. 重新下载：
```bash
ollama pull qwen2.5:7b
```

---

### Q4: 项目启动后无法调用Ollama
**A:** 检查配置文件：

1. 确认 `.env` 文件：
```ini
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://localhost:11434/v1
```

2. 确认 `config/agent_llm_config.json` 文件：
```json
{
  "config": {
    "model": "qwen2.5:7b"
  }
}
```

---

## 完整工作流程

```
1. 打开终端1，运行：ollama serve
   ↓
2. 保持终端1运行，打开终端2
   ↓
3. 在终端2验证：curl http://localhost:11434/api/tags
   ↓
4. 检查模型：ollama list
   ↓
5. 如果没有模型，下载：ollama pull qwen2.5:7b
   ↓
6. 测试模型：ollama run qwen2.5:7b "你好"
   ↓
7. 打开终端3，启动后端：python src/main.py
   ↓
8. 打开终端4，启动前端：python -m http.server 8000 --directory frontend
   ↓
9. 访问：http://localhost:8000
```

---

## 验证清单

使用前请确认：

- [ ] Ollama已安装（运行 `ollama --version`）
- [ ] Ollama服务正在运行（终端显示 "Listening on [::]:11434"）
- [ ] 可以访问 http://localhost:11434/api/tags
- [ ] qwen2.5:7b模型已下载（运行 `ollama list` 查看）
- [ ] 配置文件正确（检查.env和agent_llm_config.json）
- [ ] 项目服务启动成功（可以访问 http://localhost:8000）

---

## 需要帮助？

1. **运行诊断脚本：**
```bash
python scripts/diagnose_ollama.py
```

2. **查看详细文档：**
- 连接本地Ollama指南.md
- 连接本地Ollama-快速参考.md

3. **检查日志：**
- Ollama日志：`~/.ollama/logs/server.log`
- 项目日志：`/app/work/logs/bypass/app.log`

---

## 快速启动命令（复制粘贴）

**Windows PowerShell:**
```powershell
# 终端1 - 启动Ollama
ollama serve

# 终端2 - 检查服务
curl http://localhost:11434/api/tags

# 终端3 - 检查模型
ollama list

# 终端4 - 如果没有模型，下载
ollama pull qwen2.5:7b

# 终端5 - 启动项目
cd /workspace/projects
python src/main.py

# 终端6 - 启动前端
cd /workspace/projects
python -m http.server 8000 --directory frontend
```

**Linux/Mac Terminal:**
```bash
# 终端1 - 启动Ollama
ollama serve

# 终端2 - 检查服务
curl http://localhost:11434/api/tags

# 终端3 - 检查模型
ollama list

# 终端4 - 如果没有模型，下载
ollama pull qwen2.5:7b

# 终端5 - 启动项目
cd /workspace/projects
python src/main.py

# 终端6 - 启动前端
cd /workspace/projects
python -m http.server 8000 --directory frontend
```

---

**祝您启动成功！🚀**
