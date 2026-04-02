/**
 * 配网调度业务量智能预测系统 - 主应用逻辑
 * 深蓝科技感主题
 */

// Markdown 解析器
const md = window.markdownit({
    html: true,
    linkify: true,
    typographer: true,
    highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return '<pre class="hljs"><code>' +
                    hljs.highlight(str, lang, true).value +
                    '</code></pre>';
            } catch (__) {}
        }
        return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
    }
});

// 全局状态
const AppState = {
    isProcessing: false,
    messages: [],
    currentStreamId: null
};

/**
 * 发送消息
 */
async function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    
    if (!message || AppState.isProcessing) {
        return;
    }

    // 清空输入框
    input.value = '';
    
    // 显示用户消息
    appendMessage('user', message);
    
    // 设置处理状态
    AppState.isProcessing = true;
    setLoading(true);
    
    // 创建助手消息占位符
    const assistantMessageId = appendMessage('assistant', '', true);
    
    try {
        // 发送流式请求
        await api.streamRun(
            message,
            // 消息回调
            (data) => {
                handleStreamMessage(data, assistantMessageId);
            },
            // 错误回调
            (error) => {
                updateMessage(assistantMessageId, `❌ 错误: ${error.message}`);
                AppState.isProcessing = false;
                setLoading(false);
            },
            // 完成回调
            () => {
                AppState.isProcessing = false;
                setLoading(false);
            }
        );
    } catch (error) {
        console.error('Send message error:', error);
        updateMessage(assistantMessageId, `❌ 发送失败: ${error.message}`);
        AppState.isProcessing = false;
        setLoading(false);
    }
}

/**
 * 处理流式消息
 */
function handleStreamMessage(data, messageId) {
    console.log('Received stream data:', data);
    
    // 根据消息类型处理
    if (data.type === 'token' || data.content) {
        // 文本内容
        const content = data.content || data.token || '';
        appendToMessage(messageId, content);
    } else if (data.type === 'tool_call') {
        // 工具调用
        handleToolCall(data, messageId);
    } else if (data.type === 'prediction') {
        // 预测结果
        handlePredictionResult(data);
    } else if (data.type === 'staffing') {
        // 人员建议
        handleStaffingRecommendation(data);
    } else if (data.type === 'workload') {
        // 工作量统计
        handleWorkloadData(data);
    } else if (data.type === 'risk') {
        // 风险预警
        handleRiskAlert(data);
    } else if (data.type === 'complete') {
        // 完成
        console.log('Stream complete');
    } else if (data.type === 'error') {
        // 错误
        updateMessage(messageId, `❌ ${data.message}`);
    }
}

/**
 * 添加消息到聊天窗口
 */
function appendMessage(role, content, isStreaming = false) {
    const container = document.getElementById('messagesContainer');
    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = 'message';
    
    const avatar = role === 'user' ? '👤' : '🤖';
    const avatarClass = role === 'user' ? 'user' : 'bot';
    
    messageDiv.innerHTML = `
        <div class="message-avatar ${avatarClass}">${avatar}</div>
        <div class="message-content ${isStreaming ? 'streaming' : ''}">
            ${content || '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>'}
        </div>
    `;
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    
    AppState.messages.push({ id: messageId, role, content, isStreaming });
    
    return messageId;
}

/**
 * 更新消息内容
 */
function updateMessage(messageId, content) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;
    
    const contentDiv = messageDiv.querySelector('.message-content');
    if (contentDiv) {
        contentDiv.innerHTML = md.render(content);
        contentDiv.classList.remove('streaming');
        
        // 滚动到底部
        const container = document.getElementById('messagesContainer');
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * 追加内容到消息
 */
function appendToMessage(messageId, content) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;
    
    const contentDiv = messageDiv.querySelector('.message-content');
    if (contentDiv) {
        // 移除打字指示器
        const typingIndicator = contentDiv.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        
        // 追加内容
        const currentText = contentDiv.innerText || '';
        contentDiv.innerHTML = md.render(currentText + content);
        
        // 滚动到底部
        const container = document.getElementById('messagesContainer');
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * 处理工具调用
 */
function handleToolCall(data, messageId) {
    const toolName = data.name || '未知工具';
    const toolArgs = data.args || {};
    
    const toolDiv = document.createElement('div');
    toolDiv.style.cssText = 'margin-top: 8px; padding: 8px 12px; background: rgba(6, 182, 212, 0.1); border-left: 2px solid var(--accent-cyan); border-radius: 4px; font-size: 12px;';
    toolDiv.innerHTML = `
        <div style="color: var(--accent-cyan); font-weight: 500;">🔧 调用工具: ${toolName}</div>
        <div style="color: var(--text-muted); margin-top: 4px;">
            ${Object.entries(toolArgs).map(([k, v]) => `<span style="margin-right: 8px;">${k}: ${v}</span>`).join('')}
        </div>
    `;
    
    const messageDiv = document.getElementById(messageId);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        if (contentDiv) {
            contentDiv.appendChild(toolDiv);
        }
    }
}

/**
 * 处理预测结果
 */
function handlePredictionResult(data) {
    if (data.chart) {
        // 更新图表
        if (typeof updateWorkloadData === 'function') {
            updateWorkloadData({ workloadTimeline: data.chart });
        }
    }
    
    if (data.summary) {
        console.log('Prediction summary:', data.summary);
    }
}

/**
 * 处理人员建议
 */
function handleStaffingRecommendation(data) {
    // 更新当值人员信息
    if (data.currentStaff !== undefined) {
        document.getElementById('currentStaff').textContent = data.currentStaff + '人';
    }
    if (data.suggestedStaff !== undefined) {
        document.getElementById('suggestedStaff').textContent = data.suggestedStaff + '人';
    }
    if (data.staffCapacity !== undefined) {
        document.getElementById('staffCapacity').textContent = data.staffCapacity.toFixed(1);
    }
    if (data.isOverload !== undefined) {
        const statusEl = document.getElementById('overloadStatus');
        statusEl.textContent = data.isOverload ? '是' : '否';
        statusEl.className = 'status-value ' + (data.isOverload ? 'warning' : 'success');
    }
}

/**
 * 处理工作量数据
 */
function handleWorkloadData(data) {
    if (typeof updateWorkloadData === 'function') {
        updateWorkloadData(data);
    }
}

/**
 * 处理风险预警
 */
function handleRiskAlert(data) {
    // 可以在这里更新风险预警面板
    console.log('Risk alert:', data);
}

/**
 * 快速预测
 */
function quickPredict(type) {
    const messages = {
        today: '请预测今天的调度业务量，并提供人员配置建议。',
        week: '请预测未来7天的调度业务量趋势，分析峰值时段和风险点。',
        month: '请预测本月的调度业务量，生成月度决策报告。'
    };
    
    const input = document.getElementById('userInput');
    input.value = messages[type];
    sendMessage();
}

/**
 * 快速操作
 */
function quickAction(type) {
    const messages = {
        staffing: '请根据当前业务量预测，提供值班人员调整建议。',
        risk: '请分析当前业务风险点，并提供预警建议。',
        report: '请生成一份完整的配网调度业务量预测决策报告。',
        workload: '请统计当前工作量当量，分析各时段业务情况。'
    };
    
    const input = document.getElementById('userInput');
    input.value = messages[type];
    sendMessage();
}

/**
 * 刷新数据
 */
function refreshData() {
    // 重新初始化图表
    if (typeof initAllCharts === 'function') {
        initAllCharts();
    }
    
    // 更新最后更新时间
    updateLastUpdate();
    
    // 显示提示
    appendMessage('assistant', '🔄 数据已刷新，所有图表已更新。');
}

/**
 * 清空聊天
 */
function clearChat() {
    if (confirm('确定要清空所有对话记录吗？')) {
        const container = document.getElementById('messagesContainer');
        container.innerHTML = `
            <div class="message">
                <div class="message-avatar bot">🤖</div>
                <div class="message-content">
                    <p style="color: var(--accent-cyan); font-weight: 600; margin-bottom: 8px;">⚡ 对话已清空</p>
                    <p style="color: var(--text-secondary);">有什么我可以帮助您的吗？</p>
                </div>
            </div>
        `;
        AppState.messages = [];
    }
}

/**
 * 设置加载状态
 */
function setLoading(loading) {
    const sendBtn = document.getElementById('sendBtn');
    const overlay = document.getElementById('loadingOverlay');
    
    if (sendBtn) {
        sendBtn.disabled = loading;
        sendBtn.innerHTML = loading 
            ? '<span>处理中...</span><span class="loading-spinner" style="width: 16px; height: 16px; border-width: 2px;"></span>'
            : '<span>发送</span><span>⚡</span>';
    }
    
    if (overlay) {
        if (loading) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }
}

/**
 * 处理键盘事件
 */
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

/**
 * 格式化时间
 */
function formatTime(date) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

/**
 * 更新最后更新时间
 */
function updateLastUpdate() {
    const el = document.getElementById('lastUpdate');
    if (el) {
        el.textContent = new Date().toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
}

/**
 * 更新当前时间
 */
function updateCurrentTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('zh-CN', { hour12: false });
    const timeEl = document.getElementById('currentTime');
    if (timeEl) {
        timeEl.textContent = timeStr;
    }
}

/**
 * 获取天气数据
 */
async function updateWeatherData() {
    try {
        const response = await fetch('/api/weather');
        const result = await response.json();
        
        if (result.success && result.data) {
            const data = result.data;
            const weatherEl = document.getElementById('weatherText');
            
            if (weatherEl) {
                weatherEl.textContent = `${data.text} ${data.temp}°C`;
            }
        }
    } catch (error) {
        console.log('Weather data not available');
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 更新最后更新时间
    updateLastUpdate();
    setInterval(updateLastUpdate, 60000);
    
    // 更新当前时间（每秒更新）
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // 更新天气数据
    updateWeatherData();
    setInterval(updateWeatherData, 3600000);
    
    // 聚焦输入框
    const inputEl = document.getElementById('userInput');
    if (inputEl) {
        inputEl.focus();
    }
    
    console.log('⚡ 配网调度业务量智能预测系统已加载');
});
