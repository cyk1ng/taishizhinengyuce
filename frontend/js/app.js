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
    
    if (data.type === 'token' || data.content) {
        const content = data.content || data.token || '';
        appendToMessage(messageId, content);
    } else if (data.type === 'tool_call') {
        handleToolCall(data, messageId);
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
    messageDiv.className = `flex items-start space-x-3 message-bubble ${role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`;
    
    const avatar = role === 'user' ? '👤' : '🤖';
    const avatarBg = role === 'user' 
        ? 'bg-gradient-to-br from-gray-600 to-gray-700' 
        : 'bg-gradient-to-br from-cyan-500 to-blue-600';
    
    messageDiv.innerHTML = `
        <div class="flex-shrink-0 w-10 h-10 ${avatarBg} rounded-full flex items-center justify-center text-xl shadow-lg ${role === 'assistant' ? 'shadow-cyan-500/50' : ''}">
            ${avatar}
        </div>
        <div class="flex-1 ${role === 'user' ? 'text-right' : ''}">
            <div class="${role === 'user' ? 'bg-blue-600/30 border-blue-400/30' : 'bg-gradient-to-r from-gray-700 to-gray-800 border-cyan-500/20'} rounded-lg px-4 py-3 shadow-lg inline-block ${role === 'user' ? 'text-left' : ''} border">
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
        const typingIndicator = contentDiv.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        
        const currentText = contentDiv.innerText || '';
        contentDiv.innerHTML = md.render(currentText + content);
        
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
        <div class="tool-call-header">⚡ 执行工具: ${toolName}</div>
        <div class="text-xs text-gray-400 font-mono">
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
        chartManager.updatePredictionChart(data.chart.labels, data.chart.values);
    }
    
    if (data.summary) {
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
        recDiv.className = 'bg-gradient-to-r from-orange-900/30 to-yellow-900/30 rounded p-2 border border-orange-500/20';
        recDiv.innerHTML = `
            <div class="flex items-center justify-between mb-1">
                <span class="font-bold text-orange-300 text-xs font-mono">${rec.title}</span>
                <span class="tag ${getTagClass(rec.priority)}">${rec.priority}</span>
            </div>
            <p class="text-gray-300 text-xs font-mono">${rec.description}</p>
            ${rec.count ? `<div class="mt-1 text-xs"><span class="highlight-number text-sm">${rec.count}</span> <span class="text-gray-400">人</span></div>` : ''}
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
        alertDiv.className = `p-2 rounded text-xs ${getRiskClass(alert.level)}`;
        alertDiv.innerHTML = `
            <div class="flex items-center mb-1">
                <span class="mr-1">${getRiskIcon(alert.level)}</span>
                <span class="font-bold font-mono">${alert.title}</span>
            </div>
            <p class="text-gray-300 ml-4 font-mono">${alert.description}</p>
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
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full flex items-center justify-center text-xl shadow-lg shadow-cyan-500/50">
                    🤖
                </div>
                <div class="flex-1">
                    <div class="bg-gradient-to-r from-gray-700 to-gray-800 rounded-lg px-4 py-3 shadow-lg border border-cyan-500/20">
                        <p class="text-cyan-100 font-mono text-sm">⚡ 对话已清空。有什么我可以帮助您的吗？</p>
                    </div>
                </div>
            </div>
        `;
        AppState.messages = [];
        chartManager.clearAllCharts();
        
        document.getElementById('staffingRecommendations').innerHTML = `
            <div class="text-center text-gray-500 text-xs py-6 font-mono">
                <div class="text-2xl mb-2">📊</div>
                <div>暂无人员建议</div>
            </div>
        `;
        document.getElementById('riskAlerts').innerHTML = `
            <div class="text-center text-gray-500 text-xs py-6 font-mono">
                <div class="text-2xl mb-2">✓</div>
                <div>系统运行正常</div>
            </div>
        `;
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
    sendBtn.innerHTML = loading 
        ? '<span class="flex items-center space-x-2"><span>处理中</span><span class="text-lg animate-spin">⚡</span></span>'
        : '<span class="flex items-center space-x-2"><span>发送</span><span class="text-lg">⚡</span></span>';
    
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
    setInterval(updateLastUpdate, 60000);
    
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

document.getElementById('loadingOverlay').addEventListener('click', function(e) {
    if (e.target === this && !AppState.isProcessing) {
        setLoading(false);
    }
});
