/**
 * 配网调度业务量智能预测系统 - 主应用逻辑
 * 深蓝科技感主题
 */

// 懒加载 markdown-it + highlight.js
var _md = null;
var _hljs = null;

function _ensureMd() {
    if (_md) return Promise.resolve(_md);
    return new Promise(function(resolve) {
        if (typeof window.markdownit === 'function') {
            _initMd();
            resolve(_md);
            return;
        }
        var _bp = (window.BASE_PATH || '');
        var s = document.createElement('script');
        s.src = _bp + '/vendor/markdown-it.min.js';
        s.onload = function() {
            var s2 = document.createElement('script');
            s2.src = _bp + '/vendor/highlight.min.js';
            s2.onload = function() { _initMd(); resolve(_md); };
            document.head.appendChild(s2);
        };
        document.head.appendChild(s);
    });
}

function _initMd() {
    _hljs = window.hljs;
    _md = window.markdownit({
        html: true,
        linkify: true,
        typographer: true,
        highlight: function (str, lang) {
            if (lang && _hljs && _hljs.getLanguage(lang)) {
                try {
                    return '<pre class="hljs"><code>' +
                        _hljs.highlight(str, lang, true).value +
                        '</code></pre>';
                } catch (__) {}
            }
            return '<pre class="hljs"><code>' + str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</code></pre>';
        }
    });
}

/** 动态加载脚本 */
function _loadScript(src) {
    return new Promise(function(resolve, reject) {
        var s = document.createElement('script');
        s.src = src;
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
    });
}

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
    // 懒加载 markdown-it 和 highlight.js（用户在打字时后台下载）
    if (!_md && !window.__loadingMd) {
        window.__loadingMd = true;
        _loadScript((window.BASE_PATH || '') + '/vendor/markdown-it.min.js').then(function() {
            _loadScript((window.BASE_PATH || '') + '/vendor/highlight.min.js').then(function() {
                _ensureMd();
            });
        });
    }
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
    console.log('Received data:', JSON.stringify(data));
    
    // 1. token / message 类型 - 流式文本
    if (data.type === 'token' || data.type === 'message') {
        const content = data.content || data.token || data.text || data.message || '';
        if (content) {
            appendToMessage(messageId, content);
            return;
        }
    }
    
    // 2. 特殊类型处理（预测、人员建议、工作量等）
    if (data.type === 'prediction') {
        handlePredictionResult(data);
        return;
    } else if (data.type === 'staffing') {
        handleStaffingRecommendation(data);
        return;
    } else if (data.type === 'workload') {
        handleWorkloadData(data);
        return;
    } else if (data.type === 'risk') {
        handleRiskAlert(data);
        return;
    }
    
    // 3. workflow_end - 工作流完成，提取 output 内容
// workflow_end - 工作流完成
if (data.type === 'workflow_end') {
    if (data.output && data.output.messages) {
        const msgs = data.output.messages;
        let displayText = '';
        // 从后往前找：先找有文字的最后一条AI消息
        for (let i = msgs.length - 1; i >= 0; i--) {
            const msg = msgs[i];
            if (msg.type === 'ai' && msg.content) {
                displayText = msg.content;
                break;
            }
        }
        // 如果AI有文字回复，直接显示
        if (displayText) {
            // 检查是否包含 JSON/代码，如果是则过滤掉
            if (displayText.startsWith('{') || displayText.includes('"success"') || 
                displayText.includes('"data"') || displayText.includes('"message"')) {
                displayText = '✅ 分析已完成。如有需要，请进一步提出具体问题。';
            }
            appendToMessage(messageId, displayText);
            return;
        }
        // AI没有文字回复 → 用友好的中文提示，不要展示原始JSON
        displayText = '✅ 已获取到相关数据，请告诉我您想具体了解哪些信息？';
        appendToMessage(messageId, displayText);
    }
    return;
}

    
    // 4. message_end - 消息结束
    if (data.type === 'message_end') {
        if (data.message) appendToMessage(messageId, data.message);
        else if (data.content) appendToMessage(messageId, data.content);
        return;
    }
    
    // 5. 无 type 但有 content/text 的纯文本
    const content = data.content || data.token || data.text || data.message || data.output || '';
    if (content && typeof content === 'string') {
        appendToMessage(messageId, content);
        return;
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
    _replaceEmojiIcons();
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
        contentDiv.innerHTML = _md ? _md.render(content) : content.replace(/\n/g, '<br>');
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
        
        // 追加内容，同时过滤掉 <tool_call> 标签（流式传输时实时清理）
        const currentText = contentDiv.innerText || '';
        const rawText = currentText + content;
        // 1. 移除完整的 <tool_call>...</tool_call> 块
        // 2. 移除末尾未闭合的 <tool_call>... 部分
        const filteredText = rawText
            .replace(/<tool_call>[\s\S]*?<\/tool_call>/g, '')
            .replace(/<tool_call>[\s\S]*$/gm, '')
            .trim();
        contentDiv.innerHTML = _md ? _md.render(filteredText) : filteredText;
        
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
    const toolResult = data.result || '';
    
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
    
    // 尝试解析工具返回的 JSON 数据
    if (toolResult && typeof toolResult === 'string') {
        try {
            const parsedResult = JSON.parse(toolResult);
            
            // 处理工作量看板数据
            if (parsedResult.success && parsedResult.hourly_details) {
                handleWorkloadData(parsedResult);
            }
            
            // 处理其他类型的工具返回数据
            if (parsedResult.success && parsedResult.weights) {
                // 权重配置，不需要特殊处理
                console.log('Received weights config');
            }
            
            if (parsedResult.success && parsedResult.analysis) {
                // 人力资源分析结果
                handleStaffingRecommendation({
                    currentStaff: (parsedResult.workload_summary && parsedResult.workload_summary.total_equivalent) || 0,
                    suggestedStaff: parsedResult.analysis.total_shortage_hours || 0,
                    staffCapacity: (parsedResult.workload_summary && parsedResult.workload_summary.total_equivalent) || 0,
                    isOverload: parsedResult.analysis.total_shortage_hours > 0
                });
            }
            
        } catch (e) {
            // 不是 JSON 格式，忽略
            console.log('Tool result is not JSON format');
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
        const capEl = document.getElementById('staffCapacity');
        if (capEl) capEl.textContent = data.staffCapacity.toFixed(1);
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
    // 直接更新看板数据
    updateDashboardWithData(data);
    
    // 同时通过图表函数更新
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
    // 重新加载真实数据
    loadRealTimeData();
    
    // 更新最后更新时间
    updateLastUpdate();
}

/**
 * 加载实时数据
 * 通过发送对话请求给AI，获取数据库中的真实数据
 */
async function loadRealTimeData() {
    try {
        // 优先使用预加载数据（页面内联 script 提前发起的 fetch）
        if (window._wdPromise) {
            var promise = window._wdPromise;
            window._wdPromise = null; // 仅用一次
            var result = await promise;
            if (result && result.success) {
                updateDashboardWithData(result);
                return;
            }
        }
        
        // 发送请求给后端获取数据
        const response = await fetch(`${window.BASE_PATH}/api/workload_dashboard`);
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                updateDashboardWithData(result);
                return;
            }
        }
        
        // 如果API不可用，通过对话获取数据
        await fetchWorkloadViaChat();
        
    } catch (error) {
        console.log('API not available, using chat-based data loading');
        // 如果API不可用，通过对话获取数据
        await fetchWorkloadViaChat();
    }
}

/**
 * 通过对话方式获取工作量数据
 */
async function fetchWorkloadViaChat() {
    const input = document.getElementById('userInput');
    if (!input) return;
    
    // 清空输入框并填入请求
    const originalValue = input.value;
    input.value = '请获取今日工作量看板数据，并更新界面上的图表和统计卡片。返回的数据请包含小时粒度的计划任务数、非计划任务数、工作当量、值班人员数等信息。';
    
    // 发送消息
    await sendMessage();
    
    // 恢复原始输入
    input.value = originalValue;
}

/**
 * 使用获取到的数据更新看板
 */
function updateDashboardWithData(data) {
    if (!data || !data.success) return;
    
    const summary = data.summary || {};
    const hourlyDetails = data.hourly_details || [];
    
    // ========== 更新顶部统计卡片 ==========
    // 计划工作量
    const planTotal = summary.total_plan_count || 0;
    const inProgress = summary.in_progress || 0;
    const completed = summary.completed || 0;
    
    document.getElementById('stat-plan-total').innerHTML = `${planTotal}<span class="unit">单</span>`;
    document.getElementById('stat-plan-in-progress').textContent = inProgress;
    document.getElementById('stat-plan-completed').textContent = completed;
    
    // 非计划工作量
    const faultCount = summary.fault_count || 0;
    const defectCount = summary.defect_count || 0;
    const overloadCount = summary.overload_count || 0;
    const nonPlanTotal = faultCount + defectCount + overloadCount;
    
    document.getElementById('stat-non-plan-total').innerHTML = `${nonPlanTotal}<span class="unit">起</span>`;
    document.getElementById('stat-non-plan-fault').textContent = faultCount;
    document.getElementById('stat-non-plan-defect').textContent = defectCount;
    document.getElementById('stat-non-plan-overload').textContent = overloadCount;
    
    // 更新当值人员信息
    const totalStaff = hourlyDetails.reduce((sum, h) => sum + (h.staff_count || 0), 0) / 24 || 0;
    document.getElementById('currentStaff').textContent = Math.round(totalStaff) + '人';
    
    // 更新当值班组名称
    if (data.on_duty_team_name) {
        const teamEl = document.getElementById('onDutyTeamName');
        if (teamEl) teamEl.textContent = data.on_duty_team_name;
    }
    
    // 更新超负荷状态
    const overloadEl = document.getElementById('overloadStatus');
    if (overloadEl) {
        overloadEl.textContent = overloadCount > 0 ? '是' : '否';
        overloadEl.className = 'staff-value ' + (overloadCount > 0 ? 'warning' : 'success');
    }
    
    // 更新图表（直接传入完整 data，updateWorkloadData 会解析 hourly_details）
    if (typeof updateWorkloadData === 'function') {
        updateWorkloadData(data);
    }
    
    // 更新最后更新时间
    updateLastUpdate();
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
        _replaceEmojiIcons();
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
        if (!loading) _replaceEmojiIcons();
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
        const response = await fetch(`${window.BASE_PATH}/api/weather`);
        const result = await response.json();

        if (result.success && result.data) {
            const data = result.data;

            // 新格式: 温度区段 降水量 风力 极端天气
            const tempMin = data.tempMin || 25;
            const tempMax = data.tempMax || 35;
            const precipitation = data.precipitation || '小';
            const wind = data.wind || '小';
            const extreme = data.extreme || '';

            // 更新天气卡片
            const weatherTempEl = document.getElementById('weather-temp');
            const weatherPrecipEl = document.getElementById('weather-precipitation');
            const weatherWindEl = document.getElementById('weather-wind');
            const weatherExtremeEl = document.getElementById('weather-extreme');
            const weatherConditionIconEl = document.getElementById('weather-condition-icon');

            if (weatherTempEl) {
                weatherTempEl.textContent = `${tempMin}~${tempMax}℃`;
            }
            if (weatherPrecipEl) {
                weatherPrecipEl.textContent = precipitation;
            }
            if (weatherWindEl) {
                weatherWindEl.textContent = wind;
            }
            if (weatherExtremeEl) {
                weatherExtremeEl.textContent = extreme || '无';
            }
            if (weatherConditionIconEl) {
                // 根据天气情况选择图标
                let icon = '☀️';
                if (precipitation === '大') {
                    icon = '🌧️';
                } else if (precipitation === '中') {
                    icon = '🌦️';
                } else if (extreme && extreme.includes('雷')) {
                    icon = '⛈️';
                } else if (extreme && extreme.includes('雪')) {
                    icon = '❄️';
                } else if (extreme && extreme.includes('寒潮')) {
                    icon = '🥶';
                } else if (extreme && extreme.includes('暴')) {
                    icon = '🌪️';
                } else if (wind === '大') {
                    icon = '💨';
                }
                weatherConditionIconEl.textContent = icon;
                _replaceEmojiIcons();
            }
        }
    } catch (error) {
        console.log('Weather data not available');
        // 使用默认值
        const weatherTempEl = document.getElementById('weather-temp');
        const weatherPrecipEl = document.getElementById('weather-precipitation');
        const weatherWindEl = document.getElementById('weather-wind');
        const weatherExtremeEl = document.getElementById('weather-extreme');
        if (weatherTempEl) weatherTempEl.textContent = '--~--℃';
        if (weatherPrecipEl) weatherPrecipEl.textContent = '--';
        if (weatherWindEl) weatherWindEl.textContent = '--';
        if (weatherExtremeEl) weatherExtremeEl.textContent = '--';
    }
}

/**
 * 显示天气详情弹窗
 */
function showWeatherModal(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    // 创建弹窗
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content weather-modal-content" id="weather-modal">
            <div class="modal-header">
                <h2 id="weather-modal-title">天气详情</h2>
                <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">✕</button>
            </div>
            <div class="modal-body" id="weather-modal-body">
                <!-- 查看模式 -->
                <div id="weather-view-mode">
                    <div class="weather-detail-grid">
                        <div class="weather-detail-item">
                            <span class="weather-detail-icon">🌡️</span>
                            <div class="weather-detail-info">
                                <span class="weather-detail-label">温度范围</span>
                                <span class="weather-detail-value" id="modal-weather-temp">--~--℃</span>
                            </div>
                        </div>
                        <div class="weather-detail-item">
                            <span class="weather-detail-icon">💧</span>
                            <div class="weather-detail-info">
                                <span class="weather-detail-label">降水量级别</span>
                                <span class="weather-detail-value" id="modal-weather-precip">--</span>
                            </div>
                        </div>
                        <div class="weather-detail-item">
                            <span class="weather-detail-icon">🌬️</span>
                            <div class="weather-detail-info">
                                <span class="weather-detail-label">风力级别</span>
                                <span class="weather-detail-value" id="modal-weather-wind">--</span>
                            </div>
                        </div>
                        <div class="weather-detail-item">
                            <span class="weather-detail-icon">⚠️</span>
                            <div class="weather-detail-info">
                                <span class="weather-detail-label">极端天气</span>
                                <span class="weather-detail-value" id="modal-weather-extreme">--</span>
                            </div>
                        </div>
                    </div>
                    <div class="weather-action-buttons">
                        <button class="modal-btn primary" id="weather-edit-btn">修改天气</button>
                        <button class="modal-btn secondary" id="weather-close-view-btn">关闭</button>
                    </div>
                </div>

                <!-- 编辑模式 -->
                <div id="weather-edit-mode" style="display: none;">
                    <div class="weather-edit-form">
                        <div class="form-group">
                            <label for="edit-weather-temp">温度范围：</label>
                            <input type="text" id="edit-weather-temp" placeholder="例如：25~35℃">
                        </div>
                        <div class="form-group">
                            <label for="edit-weather-precip">降水量级别：</label>
                            <select id="edit-weather-precip">
                                <option value="小">小（&lt;=9.9mm）</option>
                                <option value="中">中（10-24.9mm）</option>
                                <option value="大">大（&gt;=25mm）</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="edit-weather-wind">风力级别：</label>
                            <select id="edit-weather-wind">
                                <option value="小">小（&lt;=6级）</option>
                                <option value="中">中（7-10级）</option>
                                <option value="大">大（&gt;=11级）</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="edit-weather-extreme">极端天气：</label>
                            <select id="edit-weather-extreme">
                                <option value="">无</option>
                                <option value="暴雨">暴雨</option>
                                <option value="雷雨">雷雨</option>
                                <option value="大雪">大雪</option>
                                <option value="暴雪">暴雪</option>
                                <option value="寒潮">寒潮</option>
                                <option value="冰雹">冰雹</option>
                                <option value="沙尘暴">沙尘暴</option>
                            </select>
                        </div>
                    </div>
                    <div class="weather-action-buttons">
                        <button class="modal-btn primary" id="weather-save-btn">保存</button>
                        <button class="modal-btn secondary" id="weather-cancel-btn">取消</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // 获取当前天气数据
    const tempEl = document.getElementById('weather-temp');
    const currentTemp = tempEl ? tempEl.textContent : '--~--℃';
    const currentPrecip = document.getElementById('weather-precipitation') ? document.getElementById('weather-precipitation').textContent : '--';
    const currentWind = document.getElementById('weather-wind') ? document.getElementById('weather-wind').textContent : '--';
    const currentExtreme = document.getElementById('weather-extreme') ? document.getElementById('weather-extreme').textContent : '--';


    // 填充查看模式数据
    document.getElementById('modal-weather-temp').textContent = currentTemp;
    document.getElementById('modal-weather-precip').textContent = currentPrecip;
    document.getElementById('modal-weather-wind').textContent = currentWind;
    document.getElementById('modal-weather-extreme').textContent = currentExtreme;

    // 填充编辑模式数据
    document.getElementById('edit-weather-temp').value = currentTemp;
    document.getElementById('edit-weather-precip').value = currentPrecip === '--' ? '小' : currentPrecip;
    document.getElementById('edit-weather-wind').value = currentWind === '--' ? '小' : currentWind;
    document.getElementById('edit-weather-extreme').value = currentExtreme === '--' || currentExtreme === '无' ? '' : currentExtreme;

    // 绑定事件
    const viewMode = document.getElementById('weather-view-mode');
    const editMode = document.getElementById('weather-edit-mode');
    const modalTitle = document.getElementById('weather-modal-title');

    // 修改按钮 - 切换到编辑模式
    document.getElementById('weather-edit-btn').addEventListener('click', () => {
        viewMode.style.display = 'none';
        editMode.style.display = 'block';
        modalTitle.textContent = '修改天气';
    });

    // 关闭按钮（查看模式）
    document.getElementById('weather-close-view-btn').addEventListener('click', () => {
        modal.remove();
    });

    // 保存按钮
    document.getElementById('weather-save-btn').addEventListener('click', () => {
        const newTemp = document.getElementById('edit-weather-temp').value;
        const newPrecip = document.getElementById('edit-weather-precip').value;
        const newWind = document.getElementById('edit-weather-wind').value;
        const newExtreme = document.getElementById('edit-weather-extreme').value;

        // 更新页面显示
        const weatherTempEl = document.getElementById('weather-temp');
        const weatherPrecipEl = document.getElementById('weather-precipitation');
        const weatherWindEl = document.getElementById('weather-wind');
        const weatherExtremeEl = document.getElementById('weather-extreme');

        if (weatherTempEl) weatherTempEl.textContent = newTemp;
        if (weatherPrecipEl) weatherPrecipEl.textContent = newPrecip;
        if (weatherWindEl) weatherWindEl.textContent = newWind;
        if (weatherExtremeEl) weatherExtremeEl.textContent = newExtreme || '无';

        // 更新查看模式数据
        document.getElementById('modal-weather-temp').textContent = newTemp;
        document.getElementById('modal-weather-precip').textContent = newPrecip;
        document.getElementById('modal-weather-wind').textContent = newWind;
        document.getElementById('modal-weather-extreme').textContent = newExtreme || '无';

        // 切换回查看模式
        editMode.style.display = 'none';
        viewMode.style.display = 'block';
        modalTitle.textContent = '天气详情';

        alert('天气信息已更新！');
    });

    // 取消按钮
    document.getElementById('weather-cancel-btn').addEventListener('click', () => {
        // 重置编辑表单
        document.getElementById('edit-weather-temp').value = currentTemp;
        document.getElementById('edit-weather-precip').value = currentPrecip === '--' ? '小' : currentPrecip;
        document.getElementById('edit-weather-wind').value = currentWind === '--' ? '小' : currentWind;
        document.getElementById('edit-weather-extreme').value = currentExtreme === '--' || currentExtreme === '无' ? '' : currentExtreme;

        // 切换回查看模式
        editMode.style.display = 'none';
        viewMode.style.display = 'block';
        modalTitle.textContent = '天气详情';
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有图表（默认显示0，等待真实数据）
    if (typeof initAllCharts === 'function') {
        initAllCharts();
    }
    
    // 更新最后更新时间
    updateLastUpdate();
    setInterval(updateLastUpdate, 60000);
    
    // 更新当前时间（每秒更新）
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // 更新天气数据
    updateWeatherData();
    setInterval(updateWeatherData, 3600000);
    
    // 自动加载今日实时数据
    setTimeout(() => {
        loadRealTimeData();
    }, 1000);
    
    // 更新工作量统计数据
    updateWorkloadStats();

    // 为天气卡片添加事件监听器
    const weatherCard = document.getElementById('weather-card');
    if (weatherCard) {
        weatherCard.addEventListener('click', function(event) {
            event.preventDefault();
            event.stopPropagation();
            showWeatherModal(event);
        });
    }

    console.log('⚡ 配网调度业务量智能预测系统已加载（使用假数据展示）');
});

/**
 * 显示计划工作量弹窗
 */
function showPlanWorkloadModal(event) {
    event.preventDefault();
    event.stopPropagation();
    
    // 调用后端API获取数据
    fetch(`${window.BASE_PATH}/api/plan_workload_detail`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.details) {
                const planData = {
                    maintenance: data.details.maintenance || {in_progress: 0, completed: 0, total: 0},
                    transfer: data.details.transfer || {in_progress: 0, completed: 0, total: 0},
                    equipment: data.details.equipment || {in_progress: 0, completed: 0, total: 0},
                    weekly_plan: data.details.weekly_plan || {in_progress: 0, completed: 0, total: 0},
                    protect: data.details.protect || {in_progress: 0, completed: 0, total: 0},
                    shift_allocation: data.shift_allocation || {morning: 0, afternoon: 0, night: 0}
                };
                updatePlanWorkloadModal(planData);
            }
        })
        .catch(err => {
            console.warn('API请求失败，使用兜底数据:', err);
            const fallback = {
                maintenance: {in_progress: 8, completed: 3, total: 11},
                transfer: {in_progress: 5, completed: 2, total: 7},
                equipment: {in_progress: 4, completed: 1, total: 5},
                weekly_plan: {in_progress: 12, completed: 6, total: 18},
                protect: {in_progress: 6, completed: 3, total: 9},
                shift_allocation: {morning: 20, afternoon: 18, night: 12}
            };
            updatePlanWorkloadModal(fallback);
        });
    
    // 显示弹窗
    const modal = document.getElementById('planWorkloadModal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * 更新计划工作量弹窗数据
 */
function updatePlanWorkloadModal(data) {
    // 更新计划检修
    updateCardFields('planWorkloadModal', 'maintenance', data.maintenance);
    
    // 更新转供电
    updateCardFields('planWorkloadModal', 'transfer', data.transfer);
    
    // 更新设备投退
    updateCardFields('planWorkloadModal', 'equipment', data.equipment);
    
    // 更新周计划
    updateCardFields('planWorkloadModal', 'weekly_plan', data.weekly_plan);
    
    // 更新班次分配
    document.getElementById('shift-morning-count').textContent = data.shift_allocation.morning;
    document.getElementById('shift-afternoon-count').textContent = data.shift_allocation.afternoon;
    document.getElementById('shift-night-count').textContent = data.shift_allocation.night;

    // 存储原始数据用于编辑
    window._planWorkloadOriginal = {
        maintenance: {...data.maintenance},
        transfer: {...data.transfer},
        equipment: {...data.equipment},
        weekly_plan: {...data.weekly_plan}
    };
}

/**
 * 更新弹窗中某个卡片的所有字段
 */
function updateCardFields(modalId, category, data) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    const card = modal.querySelector(`.editable-card[data-category="${category}"]`);
    if (!card) return;
    card.querySelectorAll('.field-value').forEach(el => {
        const field = el.dataset.field;
        if (field && data[field] !== undefined) {
            el.textContent = data[field];
        }
    });
    // 更新总计
    const total = card.querySelector('.field-total');
    if (total) {
        const inProgress = data.in_progress || 0;
        const completed = data.completed || 0;
        total.textContent = inProgress + completed;
    }
}

/**
 * 显示非计划工作量弹窗
 */
function showNonPlanWorkloadModal(event) {
    event.preventDefault();
    event.stopPropagation();
    
    // 调用后端API获取数据
    fetch(`${window.BASE_PATH}/api/nonplan_workload_detail`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.details) {
                const nonPlanData = {
                    fault: data.details.fault || {count: 0},
                    defect: data.details.defect || {count: 0},
                    overload: data.details.overload || {count: 0},
                    total: data.total || 0
                };
                updateNonPlanWorkloadModal(nonPlanData);
            }
        })
        .catch(err => {
            console.warn('API请求失败，使用兜底数据:', err);
            const fallback = {
                fault: {count: 8},
                defect: {count: 5},
                overload: {count: 2},
                total: 15
            };
            updateNonPlanWorkloadModal(fallback);
        });
    
    // 显示弹窗
    const modal = document.getElementById('nonPlanWorkloadModal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * 更新非计划工作量弹窗数据
 */
function updateNonPlanWorkloadModal(data) {
    // 更新故障日志
    updateCardFields('nonPlanWorkloadModal', 'fault', data.fault);
    
    // 更新异常缺陷
    updateCardFields('nonPlanWorkloadModal', 'defect', data.defect);
    
    // 更新重过载
    updateCardFields('nonPlanWorkloadModal', 'overload', data.overload);
    
    // 更新总计
    const totalEl = document.getElementById('non-plan-total-count');
    if (totalEl) {
        totalEl.textContent = data.total || 0;
    }
    
    // 存储原始数据
    window._nonPlanWorkloadOriginal = {
        fault: {...data.fault},
        defect: {...data.defect},
        overload: {...data.overload}
    };
}

/**
 * 关闭弹窗
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * 更新工作量统计数据
 */
async function updateWorkloadStats() {
    try {
        const response = await fetch(`${window.BASE_PATH}/api/workload_dashboard`);
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateDashboardWithData(data);
                return;
            }
        }
    } catch (e) {
        console.warn('workload_dashboard API 暂不可用，显示占位数据');
    }
    
    // 占位数据：API不可用时展示
    const today = new Date().toISOString().split('T')[0];
    
    // 计划工作量
    const planTotal = 0;
    const planInProgress = 0;
    const planCompleted = 0;
    
    document.getElementById('stat-plan-total').innerHTML = `${planTotal}<span class="unit">单</span>`;
    document.getElementById('stat-plan-in-progress').textContent = planInProgress;
    document.getElementById('stat-plan-completed').textContent = planCompleted;
    
    // 非计划工作量
    const faultCount = 0;
    const defectCount = 0;
    const overloadCount = 0;
    const nonPlanTotal = faultCount + defectCount + overloadCount;
    
    document.getElementById('stat-non-plan-total').innerHTML = `${nonPlanTotal}<span class="unit">起</span>`;
    document.getElementById('stat-non-plan-fault').textContent = faultCount;
    document.getElementById('stat-non-plan-defect').textContent = defectCount;
    document.getElementById('stat-non-plan-overload').textContent = overloadCount;
}

/**
 * 显示风险预警详情弹窗
 */
function showRiskModal() {
    const modal = document.getElementById('riskModal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * 显示今日待办详情弹窗
 */
function showTodoModal() {
    const modal = document.getElementById('todoModal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * 切换待办事项完成状态
 */
function toggleTodo(el) {
    const item = el.closest('.todo-detail-item');
    if (!item) return;
    
    const isDone = item.classList.contains('done');
    if (isDone) {
        item.classList.remove('done');
        item.classList.add('pending');
        el.classList.remove('checked');
        el.textContent = '';
    } else {
        item.classList.remove('pending');
        item.classList.add('done');
        el.classList.add('checked');
        el.textContent = '✓';
    }
    
    // 更新统计数字
    const totalEl = document.getElementById('todoTotalCount');
    const pendingEl = document.getElementById('todoPendingCount');
    const doneEl = document.getElementById('todoDoneCount');
    if (totalEl && pendingEl && doneEl) {
        const total = document.querySelectorAll('.todo-detail-item').length;
        const done = document.querySelectorAll('.todo-detail-item.done').length;
        const pending = total - done;
        totalEl.textContent = total;
        pendingEl.textContent = pending;
        doneEl.textContent = done;
    }
}

// ==================== 知识库 CRUD ====================

let kbCurrentPage = 1;
let kbTotalPages = 1;
const KB_API_BASE = (window.BASE_PATH || '') + '/api/knowledge';

function openKnowledgeModal() {
    document.getElementById('knowledgeModal').style.display = 'flex';
    kbLoadList();
}

function closeKnowledgeModal() {
    document.getElementById('knowledgeModal').style.display = 'none';
}

async function kbLoadList(page) {
    if (page) kbCurrentPage = page;
    const tbody = document.getElementById('kbTableBody');
    tbody.innerHTML = '<tr><td colspan="4" class="kb-empty">加载中...</td></tr>';
    
    try {
        const resp = await fetch(`${KB_API_BASE}/list?page=${kbCurrentPage}&page_size=15`);
        const data = await resp.json();
        
        const docs = data.documents || [];
        document.getElementById('kbCount').textContent = `共 ${data.total} 条`;
        
        const totalPages = Math.max(1, Math.ceil(data.total / 15));
        kbTotalPages = totalPages;
        
        if (docs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="kb-empty">知识库为空，点击"+ 新增知识"添加</td></tr>';
            document.getElementById('kbPagination').innerHTML = '';
            return;
        }
        
        let html = '';
        docs.forEach((doc, i) => {
            const idx = (kbCurrentPage - 1) * 15 + i + 1;
            const source = (doc.metadata && doc.metadata.source) || doc.source || '未命名';
            const content = doc.content || doc.document || '';
            const id = doc.id || doc.doc_id || '';
            // 截断过长内容，保留前100字符
            const shortContent = content.length > 100 ? content.substring(0, 100) + '...' : content;
            // 安全转义 onclick 参数（处理单引号）
            const safeId = escapeHtml(id).replace(/'/g, "\\'");
            const safeSource = escapeHtml(source).replace(/'/g, "\\'");
            const safeContent = escapeHtml(content).replace(/'/g, "\\'").replace(/\n/g, "\\n").replace(/\r/g, "\\r");
            html += `<tr>
                <td>${idx}</td>
                <td>${escapeHtml(source)}</td>
                <td title="${escapeHtml(content.substring(0, 300))}">${escapeHtml(shortContent)}</td>
                <td>
                    <div class="kb-actions">
                        <button class="kb-edit-btn" onclick="kbEditDoc('${safeId}', '${safeSource}', '${safeContent}')">编辑</button>
                        <button class="kb-del-btn" onclick="kbDeleteDoc('${safeId}')">删除</button>
                    </div>
                </td>
            </tr>`;
        });
        tbody.innerHTML = html;
        
        // 分页
        let pgHtml = '';
        pgHtml += `<button onclick="kbLoadList(${kbCurrentPage - 1})" ${kbCurrentPage <= 1 ? 'disabled' : ''}>&lt; 上一页</button>`;
        pgHtml += `<span>第 ${kbCurrentPage}/${totalPages} 页</span>`;
        pgHtml += `<button onclick="kbLoadList(${kbCurrentPage + 1})" ${kbCurrentPage >= totalPages ? 'disabled' : ''}>下一页 &gt;</button>`;
        document.getElementById('kbPagination').innerHTML = pgHtml;
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="kb-empty">加载失败，请刷新重试</td></tr>';
    }
}

async function kbSearch() {
    const q = document.getElementById('kbSearchInput').value.trim();
    const tbody = document.getElementById('kbTableBody');
    
    if (!q) {
        kbLoadList(1);
        return;
    }
    
    tbody.innerHTML = '<tr><td colspan="4" class="kb-empty">搜索中...</td></tr>';
    
    try {
        const resp = await fetch(`${KB_API_BASE}/search?q=${encodeURIComponent(q)}&top_k=20`);
        const data = await resp.json();
        
        const results = data.results || [];
        document.getElementById('kbCount').textContent = `搜索 ${results.length} 条`;
        document.getElementById('kbPagination').innerHTML = '';
        
        if (results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="kb-empty">未找到匹配内容</td></tr>';
            return;
        }
        
        let html = '';
        results.forEach((r, i) => {
            const source = r.source || '搜索结果';
            const content = r.content || '';
            const shortContent = content.length > 100 ? content.substring(0, 100) + '...' : content;
            html += `<tr>
                <td>${i + 1}</td>
                <td>${escapeHtml(source)}</td>
                <td title="${escapeHtml(content.substring(0, 300))}">${escapeHtml(shortContent)}</td>
                <td><span style="color:var(--accent-cyan);font-size:12px;">匹配度 ${(r.score * 100).toFixed(0)}%</span></td>
            </tr>`;
        });
        tbody.innerHTML = html;
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="kb-empty">搜索失败</td></tr>';
    }
}

function kbShowAdd() {
    document.getElementById('kbEditTitle').textContent = '➕ 新增知识';
    document.getElementById('kbEditId').value = '';
    document.getElementById('kbEditSource').value = '';
    document.getElementById('kbEditContent').value = '';
    document.getElementById('kbEditModal').style.display = 'flex';
    _replaceEmojiIcons();
}

function kbEditDoc(id, source, content) {
    document.getElementById('kbEditTitle').textContent = '✏️ 编辑知识';
    document.getElementById('kbEditId').value = id;
    document.getElementById('kbEditSource').value = decodeHtml(source);
    document.getElementById('kbEditContent').value = decodeHtml(content);
    document.getElementById('kbEditModal').style.display = 'flex';
    _replaceEmojiIcons();
}

function kbCloseEdit() {
    document.getElementById('kbEditModal').style.display = 'none';
}

async function kbSaveEdit(event) {
    event.preventDefault();
    const id = document.getElementById('kbEditId').value;
    const source = document.getElementById('kbEditSource').value.trim() || '用户手动添加';
    const content = document.getElementById('kbEditContent').value.trim();
    
    if (!content) {
        alert('请输入内容');
        return;
    }
    
    try {
        let resp;
        if (id) {
            resp = await fetch(`${KB_API_BASE}/update`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, content, source})
            });
        } else {
            resp = await fetch(`${KB_API_BASE}/add`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content, source})
            });
        }
        const result = await resp.json();
        if (result.success) {
            kbCloseEdit();
            kbLoadList(1);
        } else {
            alert('保存失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

async function kbDeleteDoc(id) {
    if (!confirm('确认删除该条知识？')) return;
    
    try {
        const resp = await fetch(`${KB_API_BASE}/delete`, {
            method: 'DELETE',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id})
        });
        const result = await resp.json();
        if (result.success) {
            kbLoadList(1);
        } else {
            alert('删除失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

// ========== 工具函数 ==========
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function decodeHtml(str) {
    if (!str) return '';
    return str.replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

// ========== 内网环境 emoji 图标替换为 SVG ==========
var _EMOJI_SVG_MAP = {
    '⚡': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13,2 4,14 11,14 10,22 20,10 13,10"/></svg>',
    '📊': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="12" width="4" height="9"/><rect x="10" y="7" width="4" height="14"/><rect x="17" y="3" width="4" height="18"/></svg>',
    '📈': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23,18 13,8 9,12 1,4"/><polyline points="17,18 23,18 23,12"/></svg>',
    '📋': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14,2 L6,2 C5.447,2 5,2.447 5,3 L5,21 C5,21.553 5.447,22 6,22 L18,22 C18.553,22 19,21.553 19,21 L19,7 L14,2 Z"/><path d="M14,2 L14,7 L19,7"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>',
    '🌐': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><ellipse cx="12" cy="12" rx="4" ry="10"/><line x1="2" y1="12" x2="22" y2="12"/></svg>',
    '👥': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="7" r="3"/><circle cx="17" cy="8" r="2.5"/><path d="M4,18 C4,14.5 7,13 9,13 C11,13 14,14.5 14,18"/><path d="M14,15.5 C14,14.5 16,13 17,13 C18,13 20,14 20,17"/></svg>',
    '🔋': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="16" height="10" rx="2"/><line x1="9" y1="10" x2="9" y2="14"/><line x1="6" y1="11" x2="6" y2="13"/><line x1="12" y1="10" x2="12" y2="14"/><line x1="18" y1="11" x2="20" y2="11" stroke-width="1.5"/><line x1="18" y1="13" x2="20" y2="13" stroke-width="1.5"/></svg>',
    '📚': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4,19.5 L4,4.5 C4,3.67 4.67,3 5.5,3 L20,3 L20,19 L5.5,19 C4.67,19 4,18.33 4,19.5 Z"/><path d="M8,7 L16,7"/><path d="M8,11 L16,11"/><path d="M8,15 L13,15"/></svg>',
    '💬': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21,11.5 C21,16.19 17.19,20 12.5,20 L4,20 L4,11.5 C4,6.81 7.81,3 12.5,3 C17.19,3 21,6.81 21,11.5 Z"/><line x1="8" y1="9" x2="16" y2="9"/><line x1="8" y1="13" x2="14" y2="13"/></svg>',
    '⚠️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29,3.86 L1.82,18 C1.33,18.87 1.98,20 3,20 L21,20 C22.02,20 22.67,18.87 22.18,18 L13.71,3.86 C13.22,3 11.78,3 11.29,3.86 Z"/><line x1="12" y1="10" x2="12" y2="14"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    '✓': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20,6 9,17 4,12"/></svg>',
    '📝': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16,2 L4,2 C3.447,2 3,2.447 3,3 L3,21 C3,21.553 3.447,22 4,22 L20,22 C20.553,22 21,21.553 21,21 L21,7 L16,2 Z"/><path d="M16,2 L16,7 L21,7"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/><circle cx="8" cy="10" r="1"/></svg>',
    '🔧': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7,6.3 C13.5,5.5 12,5 10.5,5 C6.9,5 4,7.9 4,11.5 C4,15.1 6.9,18 10.5,18 C14.1,18 17,15.1 17,11.5 C17,10 16.5,8.5 15.7,7.3"/><path d="M20,20 L14.5,14.5"/></svg>',
    '🔄': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23,4 23,10 17,10"/><polyline points="1,20 1,14 7,14"/><path d="M3.51,9 C4.73,6.59 7.25,5 10.18,5 C13.36,5 16.09,7.25 17.36,10"/><path d="M20.49,15 C19.27,17.41 16.75,19 13.82,19 C10.64,19 7.91,16.75 6.64,14"/></svg>',
    '🔌': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7,12 L7,5 C7,3.34 8.34,2 10,2 C11.66,2 13,3.34 13,5 L13,12"/><path d="M15,12 L15,5 C15,3.34 16.34,2 18,2 C19.66,2 21,3.34 21,5 L21,12"/><line x1="10" y1="12" x2="10" y2="22"/><line x1="18" y1="12" x2="18" y2="22"/><line x1="10" y1="16" x2="18" y2="16"/></svg>',
    '📅': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="16" y1="2" x2="16" y2="6"/></svg>',
    '🔥': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12,23 C16,23 19,20 19,16 C19,13 17,11 15,10 C15,12 14,14 12,14 C10,14 9,12 9,10 C7,11 5,13 5,16 C5,20 8,23 12,23 Z"/><path d="M12,3 C12,3 11,6 10,8 C13,8 14,6 14,4 C14,3 12,3 12,3 Z"/></svg>',
    '👤': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4,22 C4,16 8,14 12,14 C16,14 20,16 20,22"/></svg>',
    '💤': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><text x="6" y="16" font-size="12" font-weight="bold" fill="currentColor">Z</text><text x="11" y="13" font-size="10" font-weight="bold" fill="currentColor" opacity="0.7">Z</text><text x="15" y="10" font-size="8" font-weight="bold" fill="currentColor" opacity="0.5">Z</text></svg>',
    '🔍': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    '🔴': '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>',
    '🟡': '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>',
    '🟢': '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>',
    '🕐': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/></svg>',
    '🌤️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12,2 L12,4 M12,20 L12,22 M4.93,4.93 L6.34,6.34 M17.66,17.66 L19.07,19.07 M2,12 L4,12 M20,12 L22,12 M6.34,17.66 L4.93,19.07 M19.07,4.93 L17.66,6.34"/></svg>',
    '☀️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    '☁️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18,10 C18,6.69 15.31,4 12,4 C9.23,4 6.87,5.94 6.24,8.5 C4.46,8.87 3,10.28 3,12 C3,14.21 4.79,16 7,16 L18,16 C19.66,16 21,14.66 21,13 C21,11.34 19.66,10 18,10 Z"/></svg>',
    '🌡️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14,14.76 L14,4 C14,2.9 13.1,2 12,2 C10.9,2 10,2.9 10,4 L10,14.76 C8.8,15.41 8,16.63 8,18 C8,20.21 9.79,22 12,22 C14.21,22 16,20.21 16,18 C16,16.63 15.2,15.41 14,14.76 Z"/><line x1="12" y1="15" x2="12" y2="18"/><line x1="10" y1="18" x2="14" y2="18"/></svg>',
    '💧': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12,2 C12,2 6,8 6,14 C6,17.31 8.69,20 12,20 C15.31,20 18,17.31 18,14 C18,8 12,2 12,2 Z"/></svg>',
    '⚪': '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" opacity="0.3"><circle cx="12" cy="12" r="8"/></svg>',
    '🤖': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="14" rx="3"/><circle cx="9" cy="10" r="1.5" fill="currentColor"/><circle cx="15" cy="10" r="1.5" fill="currentColor"/><line x1="9" y1="15" x2="15" y2="15"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="8" y1="2" x2="8" y2="4"/><line x1="16" y1="2" x2="16" y2="4"/></svg>',
    '🧑': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4,22 C4,16 8,14 12,14 C16,14 20,16 20,22"/></svg>',
    '🌧️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18,10 C18,6.69 15.31,4 12,4 C9.23,4 6.87,5.94 6.24,8.5 C4.46,8.87 3,10.28 3,12 C3,14.21 4.79,16 7,16 L18,16 C19.66,16 21,14.66 21,13 C21,11.34 19.66,10 18,10 Z"/><line x1="7" y1="19" x2="8" y2="21"/><line x1="11" y1="19" x2="12" y2="21"/><line x1="15" y1="19" x2="16" y2="21"/></svg>',
    '🌦️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12,2 L12,4 M18,6 L16,8 M22,12 L20,12 M18,18 L16,16"/><path d="M18,10 C18,6.69 15.31,4 12,4 C9.23,4 6.87,5.94 6.24,8.5 C4.46,8.87 3,10.28 3,12 C3,14.21 4.79,16 7,16 L18,16 C19.66,16 21,14.66 21,13 C21,11.34 19.66,10 18,10 Z"/><line x1="7" y1="19" x2="8" y2="21"/><line x1="11" y1="19" x2="12" y2="21"/></svg>',
    '⛈️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18,10 C18,6.69 15.31,4 12,4 C9.23,4 6.87,5.94 6.24,8.5 C4.46,8.87 3,10.28 3,12 C3,14.21 4.79,16 7,16 L18,16 C19.66,16 21,14.66 21,13 C21,11.34 19.66,10 18,10 Z"/><line x1="9" y1="18" x2="10" y2="21"/><line x1="13" y1="18" x2="14" y2="21"/><line x1="11" y1="16" x2="12" y2="19"/><polyline points="12,6 10,10 13,10 11,14"/></svg>',
    '❄️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/><line x1="19.07" y1="4.93" x2="4.93" y2="19.07"/></svg>',
    '🥶': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="9" cy="10" r="1.5" fill="currentColor"/><circle cx="15" cy="10" r="1.5" fill="currentColor"/><path d="M6,17 C7,15 10,14 12,14 C14,14 17,15 18,17"/><path d="M2,8 L4,10 L6,8"/><path d="M18,8 L20,10 L22,8"/></svg>',
    '🌪️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12,2 C8,2 5,4 5,7 C5,9 7,10 10,10 C13,10 15,9 15,7 C15,5 13.5,4 12,4"/><path d="M10,10 C7,10 5,12 5,14 C5,16 7,17 10,17 C13,17 15,16 15,14"/><path d="M10,17 C8,17 6,18.5 6,20 C6,21.5 8,22 10,22"/></svg>',
    '💨': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4,6 C4,4 6,3 8,3 C10,3 12,4 12,6"/><path d="M4,12 C4,10 6,9 9,9 C12,9 14,10 14,12"/><path d="M4,18 C4,16 6,15 9,15 C12,15 14,16 14,18"/><line x1="18" y1="8" x2="22" y2="8"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="18" y1="16" x2="22" y2="16"/></svg>',
    '✏️': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17,3 C17.55,2.45 18.45,2.45 19,3 L21,5 C21.55,5.55 21.55,6.45 21,7 L19,9 L15,5 L17,3 Z"/><path d="M15,5 L4,16 L3,21 L8,20 L19,9"/></svg>',
    '➕': '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>',
};

// 替换页面中所有 emoji 图标为 SVG
function _replaceEmojiIcons() {
    var emojis = Object.keys(_EMOJI_SVG_MAP);
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    var changed = false;
    for (var i = 0; i < nodes.length; i++) {
        var node = nodes[i];
        var text = node.nodeValue;
        if (!text || text.length > 20) continue;
        for (var j = 0; j < emojis.length; j++) {
            if (text.indexOf(emojis[j]) !== -1 && node.parentElement && !node.parentElement.closest('script,style,svg')) {
                var span = document.createElement('span');
                span.className = 'svg-icon';
                span.innerHTML = _EMOJI_SVG_MAP[emojis[j]];
                node.parentElement.replaceChild(span, node);
                changed = true;
                break;
            }
        }
    }
    if (changed) console.log('[icons] emoji 已替换为 SVG 图标');
}

// DOM 加载完成后替换图标
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(_replaceEmojiIcons, 100);
});
