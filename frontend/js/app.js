/**
 * ⚡ 配网调度智能预测系统 - 主应用逻辑
 */

// Markdown 解析器配置
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

    input.value = '';
    
    appendMessage('user', message);
    
    AppState.isProcessing = true;
    setLoading(true);
    
    const assistantMessageId = appendMessage('assistant', '', true);
    
    try {
        await api.streamRun(
            message,
            (data) => {
                handleStreamMessage(data, assistantMessageId);
            },
            (error) => {
                updateMessage(assistantMessageId, `❌ 错误: ${error.message}`);
                AppState.isProcessing = false;
                setLoading(false);
            },
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
    
    if (data.type === 'token' || data.content) {
        const content = data.content || data.token || '';
        appendToMessage(messageId, content);
    } else if (data.type === 'prediction') {
        handlePredictionResult(data);
    } else if (data.type === 'staffing') {
        handleStaffingRecommendation(data);
    } else if (data.type === 'risk') {
        handleRiskAlert(data);
    } else if (data.type === 'complete') {
        console.log('Stream complete');
    } else if (data.type === 'error') {
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
    messageDiv.className = `message ${role === 'user' ? 'message-user' : 'message-bot'}`;
    
    const avatarClass = role === 'user' ? 'message-avatar-user' : 'message-avatar-bot';
    const contentClass = role === 'user' ? 'message-content-user' : 'message-content-bot';
    const avatar = role === 'user' ? '👤' : '🤖';
    
    messageDiv.innerHTML = `
        <div class="${avatarClass}">${avatar}</div>
        <div class="${contentClass}">
            <div class="message-text markdown-content">
                ${isStreaming ? '<span class="typing-dots"><span>●</span><span>●</span><span>●</span></span>' : md.render(content)}
            </div>
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
    
    const contentDiv = messageDiv.querySelector('.message-text');
    if (contentDiv) {
        contentDiv.innerHTML = md.render(content);
        
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
    
    const contentDiv = messageDiv.querySelector('.message-text');
    if (contentDiv) {
        const typingDots = contentDiv.querySelector('.typing-dots');
        if (typingDots) {
            typingDots.remove();
        }
        
        const currentText = contentDiv.innerText || '';
        contentDiv.innerHTML = md.render(currentText + content);
        
        const container = document.getElementById('messagesContainer');
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * 处理预测结果
 */
function handlePredictionResult(data) {
    if (data.chart) {
        chartManager.updatePredictionChart(data.chart.labels, data.chart.values);
    }
}

/**
 * 处理人员建议
 */
function handleStaffingRecommendation(data) {
    const container = document.getElementById('staffingRecommendations');
    if (!container || !data.recommendations) return;
    
    container.innerHTML = '';
    
    data.recommendations.forEach(rec => {
        const recDiv = document.createElement('div');
        recDiv.className = 'staffing-card';
        recDiv.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-bold text-orange-300">${rec.title}</span>
                <span class="priority-tag priority-${rec.priority}">${rec.priority}</span>
            </div>
            <p class="text-xs text-gray-400 mb-2">${rec.description}</p>
            ${rec.count ? `<div class="metric-small"><span class="text-cyan-400 font-bold text-lg">${rec.count}</span> <span class="text-gray-500 text-xs">人</span></div>` : ''}
        `;
        container.appendChild(recDiv);
    });
}

/**
 * 处理风险预警
 */
function handleRiskAlert(data) {
    const container = document.getElementById('riskAlerts');
    if (!container || !data.alerts) return;
    
    container.innerHTML = '';
    
    data.alerts.forEach(alert => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert-card alert-${alert.level}`;
        alertDiv.innerHTML = `
            <div class="flex items-center mb-2">
                <span class="text-lg mr-2">${getRiskIcon(alert.level)}</span>
                <span class="text-sm font-bold">${alert.title}</span>
            </div>
            <p class="text-xs text-gray-400 ml-7">${alert.description}</p>
        `;
        container.appendChild(alertDiv);
    });
}

/**
 * 快速预测
 */
function quickPredict(type) {
    const messages = {
        today: '⚡ 请预测今天的调度业务量，并提供人员配置建议。',
        week: '⚡ 请预测未来7天的调度业务量趋势，分析峰值时段和风险点。',
        month: '⚡ 请预测本月的调度业务量，生成月度决策报告。'
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
        staffing: '⚡ 请根据当前业务量预测，提供值班人员调整建议。',
        risk: '⚡ 请分析当前业务风险点，并提供预警建议。',
        report: '⚡ 请生成一份完整的配网调度业务量预测决策报告。'
    };
    
    const input = document.getElementById('userInput');
    input.value = messages[type];
    sendMessage();
}

/**
 * 清空聊天
 */
function clearChat() {
    if (confirm('确定要清空所有对话记录吗？')) {
        const container = document.getElementById('messagesContainer');
        container.innerHTML = `
            <div class="message message-bot">
                <div class="message-avatar-bot">🤖</div>
                <div class="message-content-bot">
                    <div class="message-text">
                        <p class="text-cyan-100 font-medium mb-3">⚡ 对话已清空。有什么我可以帮助您的吗？</p>
                    </div>
                </div>
            </div>
        `;
        AppState.messages = [];
        chartManager.clearAllCharts();
        
        document.getElementById('staffingRecommendations').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <div class="empty-text">暂无人员建议</div>
            </div>
        `;
        document.getElementById('riskAlerts').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon success">✓</div>
                <div class="empty-text">系统运行正常</div>
            </div>
        `;
    }
}

/**
 * 显示帮助
 */
function showHelp() {
    document.getElementById('helpModal').classList.remove('hidden');
}

/**
 * 关闭帮助
 */
function closeHelp() {
    document.getElementById('helpModal').classList.add('hidden');
}

/**
 * 设置加载状态
 */
function setLoading(loading) {
    const sendBtn = document.getElementById('sendBtn');
    const overlay = document.getElementById('loadingOverlay');
    
    sendBtn.disabled = loading;
    sendBtn.innerHTML = loading 
        ? '<span class="flex items-center space-x-2"><span>处理中</span><span class="text-xl animate-spin">⚡</span></span>'
        : '<span class="flex items-center space-x-2"><span>发送</span><span class="text-xl">⚡</span></span>';
    
    if (loading) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
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
 * 获取风险图标
 */
function getRiskIcon(level) {
    const icons = {
        'high': '🔴',
        'medium': '🟡',
        'low': '🟢'
    };
    return icons[level] || '⚪';
}

/**
 * 更新最后更新时间
 */
function updateLastUpdate() {
    const el = document.getElementById('lastUpdate');
    if (el) {
        el.textContent = formatTime(new Date());
    }
}

/**
 * 更新当前时间显示
 */
function updateCurrentTime() {
    const timeEl = document.getElementById('currentTime');
    if (timeEl) {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        timeEl.textContent = `${hours}:${minutes}:${seconds}`;
    }
}

/**
 * 获取真实天气数据
 */
async function updateWeatherData() {
    try {
        // 调用后端天气API
        const response = await fetch('/api/weather');
        const result = await response.json();
        
        if (result.success && result.data) {
            const data = result.data;
            
            // 更新天气显示
            const weatherEl = document.getElementById('weatherText');
            const tempEl = document.getElementById('tempText');
            const windTextEl = document.getElementById('windText');
            const windSpeedEl = document.getElementById('windSpeedText');
            
            if (weatherEl) weatherEl.textContent = data.text;
            if (tempEl) tempEl.textContent = `${data.temp}°C`;
            if (windTextEl) windTextEl.textContent = `${data.wind_dir} ${data.wind_scale}`;
            if (windSpeedEl) windSpeedEl.textContent = `${data.wind_speed}m/s`;
            
            // 如果是模拟数据，添加提示
            if (data.is_mock) {
                console.log('💡 当前使用模拟天气数据');
            }
        } else {
            console.error('获取天气数据失败:', result.error);
            // 使用备用数据
            useFallbackWeather();
        }
    } catch (error) {
        console.error('天气API调用失败:', error);
        // 使用备用数据
        useFallbackWeather();
    }
}

/**
 * 使用备用天气数据
 */
function useFallbackWeather() {
    const weatherEl = document.getElementById('weatherText');
    const tempEl = document.getElementById('tempText');
    const windTextEl = document.getElementById('windText');
    const windSpeedEl = document.getElementById('windSpeedText');
    
    if (weatherEl) weatherEl.textContent = '晴';
    if (tempEl) tempEl.textContent = '25°C';
    if (windTextEl) windTextEl.textContent = '微风';
    if (windSpeedEl) windSpeedEl.textContent = '2.5m/s';
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 更新最后更新时间
    updateLastUpdate();
    setInterval(updateLastUpdate, 60000);
    
    // 更新当前时间（每秒更新）
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // 更新天气数据（每小时更新一次）
    updateWeatherData();
    setInterval(updateWeatherData, 3600000);
    
    // 聚焦输入框
    document.getElementById('userInput').focus();
    
    console.log('⚡ 配网调度智能预测系统已加载');
});

// 点击模态框外部关闭
document.getElementById('helpModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeHelp();
    }
});

// 添加打字点动画样式
const style = document.createElement('style');
style.textContent = `
    .typing-dots span {
        animation: typing-dot 1.4s infinite;
        opacity: 0;
        color: #00d4ff;
    }
    .typing-dots span:nth-child(1) { animation-delay: 0s; }
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes typing-dot {
        0%, 60%, 100% { opacity: 0; }
        30% { opacity: 1; }
    }
    
    .staffing-card {
        background: linear-gradient(135deg, rgba(251, 146, 60, 0.1), rgba(234, 88, 12, 0.05));
        border: 1px solid rgba(251, 146, 60, 0.2);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
    
    .priority-tag {
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .priority-高 {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
    }
    
    .priority-中 {
        background: rgba(251, 191, 36, 0.2);
        color: #fbbf24;
    }
    
    .priority-低 {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
    }
    
    .alert-card {
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
    
    .alert-high {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1));
        border-left: 3px solid #ef4444;
    }
    
    .alert-medium {
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(245, 158, 11, 0.1));
        border-left: 3px solid #fbbf24;
    }
    
    .alert-low {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.1));
        border-left: 3px solid #22c55e;
    }
`;
document.head.appendChild(style);
