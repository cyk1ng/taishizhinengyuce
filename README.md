# 配网调度业务量智能预测系统

一个基于 AI 的配网调度业务量智能预测与人员决策支持系统，提供专业的业务量预测、人员配置建议和风险预警功能。

## 🎯 核心功能

- **多源数据融合**：整合历史调度、天气、节假日、设备状态等数据
- **业务量预测**：基于 AI 预测未来调度业务量趋势
- **人员决策支持**：生成科学的值班人员调整建议
- **风险预警**：识别业务量异常和潜在风险

## 📁 项目结构

```
.
├── frontend/              # 前端界面
│   ├── index.html        # 主页面
│   ├── css/              # 样式文件
│   ├── js/               # JavaScript逻辑
│   └── assets/           # 资源文件
├── src/                   # 源代码
│   ├── agents/           # Agent代码
│   ├── tools/            # 工具定义
│   └── main.py           # 主入口
├── config/                # 配置文件
├── assets/                # 数据文件
├── .env.example           # 环境变量模板
└── README.md              # 说明文档
```

## 🚀 快速开始

### 方式1：使用启动脚本（推荐）

**Windows:**
```bash
# 双击运行
start.bat

# 或命令行运行
start.bat
```

**Linux/Mac:**
```bash
# 添加执行权限
chmod +x start.sh

# 运行
./start.sh
```

### 方式2：手动启动

1. **配置环境变量**
   ```bash
   # 复制环境变量模板
   cp .env.example .env
   
   # 编辑 .env 文件，填写 API Key
   # COZE_WORKLOAD_IDENTITY_API_KEY=your_api_key_here
   ```

2. **启动服务**
   ```bash
   python src/main.py
   ```

3. **访问前端界面**
   
   打开浏览器访问：`http://127.0.0.1:5000`

## 💻 前端界面

启动服务后，可以通过浏览器访问图形化界面：

- **主页面**：http://127.0.0.1:5000
- **API 文档**：http://127.0.0.1:5000/docs

### 界面功能

- **智能对话**：通过自然语言与 Agent 交互
- **快速预测**：一键预测今日/7天/月度业务量
- **数据可视化**：业务量趋势图表、人员建议卡片
- **风险预警**：实时风险预警信息

详见：[前端界面文档](frontend/README.md)

## 🔧 本地开发

### 运行流程
```bash
bash scripts/local_run.sh -m flow
```

### 运行单个节点
```bash
bash scripts/local_run.sh -m node -n node_name
```

### 启动 HTTP 服务
```bash
bash scripts/http_run.sh -m http -p 5000
```

## 📝 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `COZE_WORKSPACE_PATH` | 项目根目录路径 | ✅ |
| `COZE_WORKLOAD_IDENTITY_API_KEY` | API密钥 | ✅ |
| `COZE_INTEGRATION_MODEL_BASE_URL` | 模型API地址 | ❌ |

## 📖 文档

- [前端界面文档](frontend/README.md)
- [Agent 配置说明](AGENT.md)
- [环境变量配置](.env.example)

## 🛠️ 技术栈

- **后端**：Python, FastAPI, LangChain, LangGraph
- **前端**：HTML5, CSS3, JavaScript, Tailwind CSS, Chart.js
- **AI**：大语言模型 (豆包/DeepSeek)

## 📄 License

MIT License

