/**
 * 配网调度业务量智能预测系统 - 主应用逻辑
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
    messageDiv.className = `flex items-start space-x-3 message-bubble ${role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`;
    
    const avatar = role === 'user' ? '👤' : '🤖';
    const avatarBg = role === 'user' 
        ? 'bg-gradient-to-br from-gray-500 to-gray-600' 
        : 'bg-gradient-to-br from-blue-500 to-purple-600';
    
    messageDiv.innerHTML = `
        <div class="flex-shrink-0 w-10 h-10 ${avatarBg} rounded-full flex items-center justify-center text-xl">
            ${avatar}
        </div>
        <div class="flex-1 ${role === 'user' ? 'text-right' : ''}">
            <div class="${role === 'user' ? 'bg-blue-700' : 'bg-gray-700'} rounded-lg px-4 py-3 shadow inline-block ${role === 'user' ? 'text-left' : ''}">
                <div class="message-content markdown-content ${isStreaming ? 'streaming' : ''}">${content || '<span class="typing-indicator"><span></span><span></span><span></span></span>'}</div>
            </div>
            <div class="message-timestamp text-xs mt-1 ${role === 'user' ? 'text-right' : ''}">${formatTime(new Date())}</div>
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
    toolDiv.className = 'tool-call';
    toolDiv.innerHTML = `
        <div class="tool-call-header">🔧 调用工具: ${toolName}</div>
        <div class="text-xs text-gray-400">
            ${Object.entries(toolArgs).map(([k, v]) => `<span class="tag tag-blue mr-2">${k}: ${v}</span>`).join('')}
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
        chartManager.updatePredictionChart(data.chart.labels, data.chart.values);
    }
    
    if (data.summary) {
        // 显示摘要
        console.log('Prediction summary:', data.summary);
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
        recDiv.className = 'bg-gray-700 rounded p-3 text-sm';
        recDiv.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <span class="font-semibold text-orange-300">${rec.title}</span>
                <span class="tag ${getTagClass(rec.priority)}">${rec.priority}</span>
            </div>
            <p class="text-gray-300 text-xs">${rec.description}</p>
            ${rec.count ? `<div class="mt-2 text-xs"><span class="highlight-number">${rec.count}</span> 人</div>` : ''}
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
        alertDiv.className = `p-3 rounded text-sm ${getRiskClass(alert.level)}`;
        alertDiv.innerHTML = `
            <div class="flex items-center mb-1">
                <span class="mr-2">${getRiskIcon(alert.level)}</span>
                <span class="font-semibold">${alert.title}</span>
            </div>
            <p class="text-xs text-gray-300 ml-6">${alert.description}</p>
        `;
        container.appendChild(alertDiv);
    });
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
        report: '请生成一份完整的配网调度业务量预测决策报告。'
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
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-xl">
                    🤖
                </div>
                <div class="flex-1">
                    <div class="bg-gray-700 rounded-lg px-4 py-3 shadow">
                        <p class="text-gray-100">对话已清空。有什么我可以帮助您的吗？</p>
                    </div>
                </div>
            </div>
        `;
        AppState.messages = [];
        chartManager.clearAllCharts();
        
        // 清空右侧面板
        document.getElementById('staffingRecommendations').innerHTML = '<div class="text-center text-gray-400 text-sm py-4">暂无人员建议</div>';
        document.getElementById('riskAlerts').innerHTML = '<div class="text-center text-gray-400 text-sm py-4">暂无风险预警</div>';
    }
}

/**
 * 显示帮助
 */
function showHelp() {
    document.getElementById('helpModal').classList.remove('hidden');
    document.getElementById('helpModal').classList.add('flex');
}

/**
 * 关闭帮助
 */
function closeHelp() {
    document.getElementById('helpModal').classList.add('hidden');
    document.getElementById('helpModal').classList.remove('flex');
}

/**
 * 设置加载状态
 */
function setLoading(loading) {
    const sendBtn = document.getElementById('sendBtn');
    const overlay = document.getElementById('loadingOverlay');
    
    sendBtn.disabled = loading;
    sendBtn.innerHTML = loading ? '发送中...' : '发送 ⚡';
    
    if (loading) {
        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
    } else {
        overlay.classList.add('hidden');
        overlay.classList.remove('flex');
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
 * 获取标签样式类
 */
function getTagClass(priority) {
    const classes = {
        '高': 'tag-red',
        '中': 'tag-yellow',
        '低': 'tag-green'
    };
    return classes[priority] || 'tag-blue';
}

/**
 * 获取风险样式类
 */
function getRiskClass(level) {
    const classes = {
        'high': 'risk-high',
        'medium': 'risk-medium',
        'low': 'risk-low'
    };
    return classes[level] || 'risk-low';
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
        el.textContent = new Date().toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 更新最后更新时间
    updateLastUpdate();
    setInterval(updateLastUpdate, 60000); // 每分钟更新
    
    // 聚焦输入框
    document.getElementById('userInput').focus();
    
    console.log('⚡ 配网调度业务量智能预测系统已加载');
});

// 点击模态框外部关闭
document.getElementById('helpModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeHelp();
    }
});

document.getElementById('loadingOverlay').addEventListener('click', function(e) {
    if (e.target === this && !AppState.isProcessing) {
        setLoading(false);
    }
});
