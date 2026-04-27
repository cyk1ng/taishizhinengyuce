# 连接本地Ollama - 快速参考

## 🚀 3分钟快速开始

### 1️⃣ 安装Ollama

**Windows：**
```
访问 https://ollama.com/download 下载安装
```

**macOS：**
```bash
brew install ollama
```

**Linux：**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2️⃣ 启动Ollama服务

**新开终端窗口运行：**
```bash
ollama serve
```

**确认服务运行：**
```bash
curl http://localhost:11434/api/tags
```

### 3️⃣ 下载模型

```bash
ollama pull qwen2.5:7b
```

**查看已安装的模型：**
```bash
ollama list
```

### 4️⃣ 测试模型

```bash
ollama run qwen2.5:7b "你好"
```

### 5️⃣ 启动项目

**方法1：使用快速启动脚本**

**Windows：**
```bash
双击运行：scripts\start_with_ollama.bat
```

**Linux/Mac：**
```bash
./scripts/start_with_ollama.sh
```

**方法2：手动启动**

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

**终端3 - 访问界面：**
```
浏览器打开：http://localhost:8000
```

---

## ⚙️ 配置文件

### .env 配置
```ini
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://localhost:11434/v1
```

### agent_llm_config.json 配置
```json
{
  "config": {
    "model": "qwen2.5:7b"
  }
}
```

---

## 🧪 测试连接

### 运行测试脚本
```bash
python scripts/test_ollama_connection.py
```

### 手动测试
```bash
# 测试Ollama服务
curl http://localhost:11434/api/tags

# 测试模型
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:7b",
  "prompt": "你好",
  "stream": false
}'
```

---

## 📊 可用模型

| 模型名称 | 大小 | 显存需求 | 推荐场景 |
|---------|------|---------|---------|
| qwen2.5:3b | ~2GB | 4GB | 低资源环境 |
| qwen2.5:7b | ~4.5GB | 8GB | **推荐** |
| qwen2.5:14b | ~9GB | 16GB | 高性能需求 |
| qwen2.5:32b | ~20GB | 32GB | 企业级应用 |

### 下载其他模型
```bash
ollama pull qwen2.5:3b
ollama pull qwen2.5:14b
ollama pull qwen2.5:32b
```

---

## 🔧 故障排除

### 问题1：Ollama服务无法启动
**症状：** 运行 `ollama serve` 报错

**解决方案：**
```bash
# Windows
netstat -ano | findstr :11434
taskkill /PID <进程ID> /F

# Linux/Mac
lsof -ti:11434 | xargs kill -9

# 然后重新启动
ollama serve
```

### 问题2：模型下载失败
**症状：** `ollama pull qwen2.5:7b` 报错

**解决方案：**
```bash
# 检查网络连接
ping ollama.com

# 使用代理（如果需要）
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
ollama pull qwen2.5:7b
```

### 问题3：连接超时
**症状：** 项目连接Ollama超时

**解决方案：**
```bash
# 1. 确认Ollama服务运行
curl http://localhost:11434/api/tags

# 2. 检查配置文件
cat .env | grep BASE_URL
cat config/agent_llm_config.json | grep model

# 3. 重启项目
```

### 问题4：模型响应慢
**症状：** 生成速度很慢

**解决方案：**
```bash
# 1. 使用更小的模型
ollama pull qwen2.5:3b
# 修改配置：model": "qwen2.5:3b"

# 2. 减少上下文长度
# 在agent_llm_config.json中设置
{
  "config": {
    "max_completion_tokens": 2000
  }
}

# 3. 使用GPU（如果支持）
# Ollama会自动使用GPU
```

---

## 📚 相关文档

- **连接本地Ollama指南.md** - 详细配置说明
- **本地模型快速开始.md** - 本地模型部署
- **本地模型部署指南.md** - 完整部署手册

---

## 💡 提示

1. **确保Ollama服务始终运行**
   - Windows：设置为开机自启动
   - Linux/Mac：使用systemd或launchd

2. **模型选择**
   - 首次使用：qwen2.5:3b（快速测试）
   - 日常使用：qwen2.5:7b（平衡性能）
   - 高性能：qwen2.5:14b（专业场景）

3. **性能优化**
   - 关闭不必要的程序释放内存
   - 使用SSD存储模型
   - 定期清理Ollama缓存

---

## 🎯 快速命令

```bash
# 查看Ollama版本
ollama --version

# 查看已安装的模型
ollama list

# 下载模型
ollama pull qwen2.5:7b

# 运行模型
ollama run qwen2.5:7b

# 查看模型信息
ollama show qwen2.5:7b

# 删除模型
ollama rm qwen2.5:7b

# 运行连接测试
python scripts/test_ollama_connection.py

# 使用快速启动脚本
# Windows
scripts\start_with_ollama.bat

# Linux/Mac
./scripts/start_with_ollama.sh
```

---

**最后更新：** 2026-04-24
**适用版本：** v2.0
**维护状态：** ✅ 正常维护
