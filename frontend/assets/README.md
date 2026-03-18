# 配网调度业务量智能预测系统 - 使用指南

## 🚀 5分钟快速上手

### 第一步：启动服务

**Windows 用户：**
双击 `start.bat` 文件

**Mac/Linux 用户：**
```bash
chmod +x start.sh
./start.sh
```

### 第二步：配置 API Key

如果看到错误提示，说明需要配置 API Key：

1. 打开 `.env` 文件（如果没有，复制 `.env.example`）
2. 填写你的 API Key：
   ```
   COZE_WORKLOAD_IDENTITY_API_KEY=你的API_Key
   ```

**如何获取 API Key？**
- 火山引擎：https://console.volcengine.com/ark
- Coze 平台：https://www.coze.cn/

### 第三步：访问界面

打开浏览器，访问：**http://127.0.0.1:5000**

## 💡 使用技巧

### 快速预测
点击左侧的快速预测按钮：
- **今日预测** - 预测今天的业务量
- **7天预测** - 预测未来一周趋势
- **本月预测** - 预测当月总量

### 自由对话
在输入框输入你的问题，例如：
- "预测未来7天的调度业务量"
- "明天需要多少值班人员？"
- "本周有哪些风险点？"

### 查看结果
预测结果会显示在：
- 右侧**预测趋势图** - 业务量趋势可视化
- 右侧**人员建议** - 人员配置建议
- 右侧**风险预警** - 潜在风险提示

## 📞 常见问题

**Q: 界面打不开？**
A: 确认服务已启动，检查端口 5000 是否被占用

**Q: 发送消息没反应？**
A: 检查 API Key 是否正确配置，查看浏览器控制台错误信息

**Q: 图表不显示？**
A: 需要先进行预测，预测数据才会显示在图表中

## 🎓 进阶使用

### API 调用

**流式对话：**
```bash
curl -X POST "http://127.0.0.1:5000/stream_run" \
  -H "Content-Type: application/json" \
  -d '{"message":"预测未来7天业务量"}'
```

**同步对话：**
```bash
curl -X POST "http://127.0.0.1:5000/run" \
  -H "Content-Type: application/json" \
  -d '{"message":"预测未来7天业务量"}'
```

**健康检查：**
```bash
curl http://127.0.0.1:5000/health
```

## 📧 技术支持

遇到问题？查看以下资源：
- [前端界面文档](frontend/README.md)
- [环境变量配置](.env.example)
- [Agent 说明](AGENT.md)
