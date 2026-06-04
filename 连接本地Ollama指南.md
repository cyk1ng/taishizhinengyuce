# 连接本地Ollama指南

## 📋 前提条件

1. ✅ 已安装 Ollama
2. ✅ Ollama服务已启动
3. ✅ 已下载 qwen2.5:7b 模型

---

## 🔍 步骤1：检查Ollama服务

### 1.1 检查Ollama是否已安装
```bash
ollama --version
```

**预期输出：**
```
ollama version is 0.x.x
```

**如果提示"命令不存在"，请先安装Ollama：**
- **Windows**: https://ollama.com/download
- **macOS**: `brew install ollama`
- **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`

### 1.2 检查Ollama服务是否运行
```bash
curl http://localhost:11434/api/tags
```

**预期输出：**
```json
{
  "models": [
    {
      "name": "qwen2.5:7b",
      "modified_at": "2024-xx-xx",
      "size": 4668805120
    }
  ]
}
```

**如果提示"连接被拒绝"，请启动Ollama服务：**
```bash
ollama serve
```

---

## 📥 步骤2：下载模型

### 2.1 下载qwen2.5:7b模型
```bash
ollama pull qwen2.5:7b
```

**预期输出：**
```
pulling manifest
pulling 5a1b687b8c8b...
verifying sha256 digest
writing manifest
success
```

**下载说明：**
- 模型大小：约4.5GB
- 下载时间：取决于网络速度（通常5-15分钟）
- 磁盘需求：至少5GB可用空间

### 2.2 查看已安装的模型
```bash
ollama list
```

**预期输出：**
```
NAME                ID              SIZE      MODIFIED
qwen2.5:7b          abc123...       4.5 GB    2 minutes ago
```

---

## 🔧 步骤3：配置项目

### 3.1 检查.env配置

**打开文件：** `.env`

**确认以下配置：**
```ini
COZE_WORKLOAD_IDENTITY_API_KEY=ollama
COZE_INTEGRATION_MODEL_BASE_URL=http://localhost:11434/v1
```

**配置说明：**
- `COZE_WORKLOAD_IDENTITY_API_KEY`: 本地Ollama使用固定值"ollama"
- `COZE_INTEGRATION_MODEL_BASE_URL`: Ollama服务地址（默认11434端口）

### 3.2 检查agent_llm_config.json配置

**打开文件：** `config/agent_llm_config.json`

**确认以下配置：**
```json
{
  "config": {
    "model": "qwen2.5:7b",
    "temperature": 0.3,
    "top_p": 0.9,
    "max_completion_tokens": 8000,
    "timeout": 600,
    "thinking": "disabled"
  }
}
```

**配置说明：**
- `model`: 模型名称，必须与已下载的模型名称一致
- `temperature`: 温度参数，控制随机性（0.0-1.0）
- `max_completion_tokens`: 最大完成令牌数
- `timeout`: 超时时间（秒）

---

## ✅ 步骤4：测试连接

### 4.1 运行测试脚本
```bash
python scripts/test_ollama_connection.py
```

**预期输出：**
```
============================================================
测试本地Ollama连接
============================================================

1. 测试Ollama服务...
✅ Ollama服务运行正常
   服务版本：0.x.x

   已安装的模型（1个）：
   - qwen2.5:7b (4.35GB)

2. 检查项目配置...
✅ 找到配置文件：.env
✅ 配置正确：BASE_URL指向本地Ollama
✅ 找到配置文件：config/agent_llm_config.json
   配置模型：qwen2.5:7b
✅ 模型 qwen2.5:7b 已安装

3. 测试模型调用...
✅ 模型调用成功
   模型响应：测试成功

============================================================
✅ 所有测试通过！项目可以正常使用本地Ollama
============================================================

🚀 启动项目：
   1. 确保Ollama服务正在运行：ollama serve
   2. 启动后端服务：python src/main.py
   3. 启动前端服务：python -m http.server 8000 --directory frontend
   4. 访问界面：http://localhost:8000
```

---

## 🚀 步骤5：启动项目

### 5.1 启动Ollama服务
```bash
ollama serve
```

**说明：**
- 该命令会启动Ollama服务
- 服务运行在 `http://localhost:11434`
- 保持终端打开，不要关闭

### 5.2 启动后端服务（新开一个终端）
```bash
cd /path/to/project
python src/main.py
```

**说明：**
- 启动FastAPI后端服务
- 服务运行在 `http://localhost:8000`
- 提供RESTful API接口

### 5.3 启动前端服务（新开一个终端）
```bash
cd /path/to/project
python -m http.server 8000 --directory frontend
```

**说明：**
- 启动静态文件服务器
- 访问地址：`http://localhost:8000`

### 5.4 访问界面

**打开浏览器，访问：**
```
http://localhost:8000
```

---

## 🐛 常见问题

### 问题1：提示"无法连接到Ollama服务"

**原因：** Ollama服务未启动

**解决方法：**
```bash
ollama serve
```

---

### 问题2：提示"模型未安装"

**原因：** qwen2.5:7b模型未下载

**解决方法：**
```bash
ollama pull qwen2.5:7b
```

---

### 问题3：提示"配置不正确"

**原因：** .env配置文件错误

**解决方法：**
1. 打开 `.env` 文件
2. 确认以下配置正确：
   ```ini
   COZE_WORKLOAD_IDENTITY_API_KEY=ollama
   COZE_INTEGRATION_MODEL_BASE_URL=http://localhost:11434/v1
   ```
3. 保存文件
4. 重启项目

---

### 问题4：模型调用超时

**原因：** 模型响应时间过长

**解决方法：**
1. 打开 `config/agent_llm_config.json`
2. 增加timeout值：
   ```json
   {
     "config": {
       "timeout": 1200  // 从600秒增加到1200秒
     }
   }
   ```

---

### 问题5：内存不足

**原因：** 模型需要的内存超过可用内存

**解决方法：**
1. 使用更小的模型：
   ```bash
   ollama pull qwen2.5:3b
   ```
2. 修改配置文件中的模型名称：
   ```json
   {
     "config": {
       "model": "qwen2.5:3b"
     }
   }
   ```

---

## 📚 相关文档

- **README_本地模型.md** - 本地模型部署完整文档
- **本地模型快速开始.md** - 1分钟快速部署指南
- **本地模型配置总结.md** - 配置详情和性能优化
- **本地模型部署指南.md** - 完整部署手册

---

## 🌟 优化建议

### 1. 使用GPU加速

如果有GPU，Ollama会自动使用GPU加速，大幅提升性能。

检查GPU使用情况：
```bash
ollama run qwen2.5:7b "你好"
# 在另一个终端查看GPU使用情况
nvidia-smi  # NVIDIA GPU
```

### 2. 调整模型参数

根据需要调整以下参数：

**config/agent_llm_config.json**
```json
{
  "config": {
    "temperature": 0.3,        // 降低温度，输出更确定性
    "top_p": 0.9,              // 增加top_p，提高多样性
    "max_completion_tokens": 4000  // 减少最大令牌数，加快响应
  }
}
```

### 3. 使用更小的模型

如果性能不足，可以使用更小的模型：

**选项1：qwen2.5:3b（推荐）**
```bash
ollama pull qwen2.5:3b
```
- 大小：约2GB
- 显存：4GB
- 性能：适合快速响应

**选项2：qwen2.5:1.5b（极速）**
```bash
ollama pull qwen2.5:1.5b
```
- 大小：约1GB
- 显存：2GB
- 性能：适合极低配置

### 4. 批量处理

如果有多个请求，可以使用Ollama的批量处理功能，提升吞吐量。

---

## 📊 性能参考

| 模型 | 大小 | 显存 | CPU性能 | GPU性能 |
|------|------|------|---------|---------|
| qwen2.5:1.5b | ~1GB | 2GB | ~5 tok/s | ~50 tok/s |
| qwen2.5:3b | ~2GB | 4GB | ~3 tok/s | ~40 tok/s |
| qwen2.5:7b | ~4.5GB | 8GB | ~1 tok/s | ~30 tok/s |
| qwen2.5:14b | ~9GB | 16GB | ~0.5 tok/s | ~20 tok/s |

---

## 🎯 快速检查清单

启动前请确认：

- [ ] Ollama已安装（`ollama --version`）
- [ ] Ollama服务正在运行（`ollama serve`）
- [ ] qwen2.5:7b模型已下载（`ollama list`）
- [ ] .env配置正确（指向localhost:11434）
- [ ] agent_llm_config.json配置正确（模型名为qwen2.5:7b）
- [ ] 测试脚本通过（`python scripts/test_ollama_connection.py`）

---

**配置完成时间：** 2026-04-24  
**适用版本：** v2.0  
**维护状态：** ✅ 正常维护
