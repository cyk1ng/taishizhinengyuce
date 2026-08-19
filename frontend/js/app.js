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
    
    // 页面数据加载完成 → 自动保存快照（AI 分析时使用）
    setTimeout(savePageSnapshot, 500);
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
        const response = await fetch(`${(window.BASE_PATH || '')}/api/workload_dashboard`);
        
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
    
    // 非计划工作量 - 显示开展中/已终结
    const nonPlanInProgress = summary.non_plan_in_progress || 0;
    const nonPlanCompleted = summary.non_plan_completed || 0;
    const nonPlanTotal = nonPlanInProgress + nonPlanCompleted;
    
    document.getElementById('stat-non-plan-total').innerHTML = `${nonPlanTotal}<span class="unit">起</span>`;
    document.getElementById('stat-non-plan-in-progress').textContent = nonPlanInProgress;
    document.getElementById('stat-non-plan-completed').textContent = nonPlanCompleted;
    
    // 更新当值人员信息 - 优先使用 API 返回的 on_duty_staff_count
    const onDutyStaffCount = data.on_duty_staff_count || Math.round(hourlyDetails.reduce((sum, h) => sum + (h.staff_count || 0), 0) / 24) || 0;
    document.getElementById('currentStaff').textContent = onDutyStaffCount + '人';
    
    // 更新当值班组名称
    const teamEl = document.getElementById('onDutyTeamName');
    if (teamEl) {
        teamEl.textContent = data.on_duty_team_name || 'A 班';
    }
    
    // 更新建议人数和超负荷状态
    const suggestedStaff = summary.suggested_staff || onDutyStaffCount || 5;
    document.getElementById('suggestedStaff').textContent = suggestedStaff + '人';
    
    const overloadEl = document.getElementById('overloadStatus');
    if (overloadEl) {
        const isOverload = summary.is_overload !== undefined ? summary.is_overload : (nonPlanTotal > suggestedStaff * 2);
        overloadEl.textContent = isOverload ? '是' : '否';
        overloadEl.className = 'stat-info-value ' + (isOverload ? 'warning' : 'success');
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
        const response = await fetch(`${(window.BASE_PATH || '')}/api/weather`);
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
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
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

/**
 * 快速操作：发送消息到聊天框
 */
function sendQuickMessage(text) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
    }
    sendMessage();
}

/**
 * 初始化风险预警假数据
 */
function initRiskAlerts() {
    const container = document.getElementById('riskAlerts');
    if (!container) return;
    
    // 尝试从API获取数据
    fetch(`${(window.BASE_PATH || '')}/api/risk_alerts`)
        .then(res => res.json())
        .then(data => {
            if (data && data.success && data.alerts && data.alerts.length > 0) {
                renderRiskAlerts(data.alerts);
            } else {
                // 使用假数据
                renderRiskAlerts([
                    { level: 'warning', title: '明日预测工作量偏高', desc: '预计明日工作量超出人员承载能力，建议提前调配人员' },
                    { level: 'success', title: '人员配置合理', desc: '当前值班人员数量满足工作需求' },
                    { level: 'danger', title: '设备重过载风险', desc: '2台设备存在重过载风险，需重点关注' }
                ]);
            }
        })
        .catch(() => {
            // API失败，使用假数据
            renderRiskAlerts([
                { level: 'warning', title: '明日预测工作量偏高', desc: '预计明日工作量超出人员承载能力，建议提前调配人员' },
                { level: 'success', title: '人员配置合理', desc: '当前值班人员数量满足工作需求' },
                { level: 'danger', title: '设备重过载风险', desc: '2台设备存在重过载风险，需重点关注' }
            ]);
        });
}

function renderRiskAlerts(alerts) {
    const container = document.getElementById('riskAlerts');
    if (!container) return;
    
    container.innerHTML = alerts.map(alert => {
        const icon = alert.level === 'danger' ? '🔴' : alert.level === 'warning' ? '⚠️' : '✅';
        const color = alert.level === 'danger' ? 'var(--accent-red)' : alert.level === 'warning' ? 'var(--accent-orange)' : 'var(--accent-green)';
        return `
            <div class="todo-item">
                <span style="color: ${color}; margin-right: 8px;">${icon}</span>
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">${alert.title}</div>
                    <div style="font-size: 12px; color: var(--text-secondary);">${alert.desc}</div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 初始化今日待办假数据
 */
function initTodos() {
    const container = document.getElementById('todoList');
    if (!container) return;
    
    // 尝试从API获取数据
    fetch(`${(window.BASE_PATH || '')}/api/todos`)
        .then(res => res.json())
        .then(data => {
            if (data && data.success && data.todos && data.todos.length > 0) {
                renderTodos(data.todos);
            } else {
                // 使用假数据
                renderTodos([
                    { title: '故障日志处理', status: 'pending' },
                    { title: '检修单审核', status: 'pending' },
                    { title: '操作票审核', status: 'pending' },
                    { title: '周计划确认', status: 'completed' }
                ]);
            }
        })
        .catch(() => {
            // API失败，使用假数据
            renderTodos([
                { title: '故障日志处理', status: 'pending' },
                { title: '检修单审核', status: 'pending' },
                { title: '操作票审核', status: 'pending' },
                { title: '周计划确认', status: 'completed' }
            ]);
        });
}

function renderTodos(todos) {
    const container = document.getElementById('todoList');
    if (!container) return;
    
    container.innerHTML = todos.map(todo => {
        const icon = todo.status === 'completed' ? '✅' : '⏳';
        const color = todo.status === 'completed' ? 'var(--accent-green)' : 'var(--accent-orange)';
        return `
            <div class="todo-item">
                <span style="color: ${color}; margin-right: 8px;">${icon}</span>
                <span style="flex: 1; color: var(--text-primary);">${todo.title}</span>
            </div>
        `;
    }).join('');
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
    
    // 初始化风险预警和今日待办
    initRiskAlerts();
    initTodos();

    // 为天气卡片添加事件监听器
    const weatherCard = document.getElementById('weather-card');
    if (weatherCard) {
        weatherCard.addEventListener('click', function(event) {
            event.preventDefault();
            event.stopPropagation();
            showWeatherModal(event);
        });
    }

    // 快速操作按钮点击事件
    // 快速操作按钮已改为 onclick 直接调用 sendQuickMessage

    // 初始化风险预警和今日待办假数据
    initFakeRiskAlerts();
    initFakeTodos();

    console.log(' 配网调度业务量智能预测系统已加载（使用假数据展示）');
});

/**
 * 初始化风险预警假数据
 */
function initFakeRiskAlerts() {
    const container = document.getElementById('riskAlertsContainer');
    if (!container) return;
    
    // 检查是否有真实数据
    fetch(`${(window.BASE_PATH || '')}/api/risk_alerts`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.alerts && data.alerts.length > 0) {
                renderRiskAlerts(data.alerts);
            } else {
                // 使用假数据
                const fakeAlerts = [
                    { id: 1, title: '明日预测工作量偏高', level: 'warning', desc: '预计明日工作量将达到35单，超出日常均值20%' },
                    { id: 2, title: '人员配置合理', level: 'success', desc: '当前值班人员配置充足，可满足日常工作需求' },
                    { id: 3, title: '设备重过载风险', level: 'danger', desc: '2台变压器负载率超过80%，需关注' }
                ];
                renderRiskAlerts(fakeAlerts);
            }
        })
        .catch(() => {
            // API失败，使用假数据
            const fakeAlerts = [
                { id: 1, title: '明日预测工作量偏高', level: 'warning', desc: '预计明日工作量将达到35单，超出日常均值20%' },
                { id: 2, title: '人员配置合理', level: 'success', desc: '当前值班人员配置充足，可满足日常工作需求' },
                { id: 3, title: '设备重过载风险', level: 'danger', desc: '2台变压器负载率超过80%，需关注' }
            ];
            renderRiskAlerts(fakeAlerts);
        });
}

/**
 * 渲染风险预警
 */
function renderRiskAlerts(alerts) {
    const container = document.getElementById('riskAlertsContainer');
    if (!container) return;
    
    container.innerHTML = alerts.map(alert => `
        <div class="risk-alert-item ${alert.level}">
            <span class="risk-alert-icon">${alert.level === 'danger' ? '🔴' : alert.level === 'warning' ? '🟡' : ''}</span>
            <div class="risk-alert-content">
                <div class="risk-alert-title">${alert.title}</div>
                <div class="risk-alert-desc">${alert.desc}</div>
            </div>
        </div>
    `).join('');
}

/**
 * 初始化今日待办假数据
 */
function initFakeTodos() {
    const container = document.getElementById('todoContainer');
    if (!container) return;
    
    // 检查是否有真实数据
    fetch(`${(window.BASE_PATH || '')}/api/todos`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.todos && data.todos.length > 0) {
                renderTodos(data.todos);
            } else {
                // 使用假数据
                const fakeTodos = [
                    { id: 1, title: '故障日志处理', priority: 'high', status: 'pending' },
                    { id: 2, title: '检修单审核', priority: 'medium', status: 'pending' },
                    { id: 3, title: '操作票审核', priority: 'medium', status: 'pending' },
                    { id: 4, title: '周计划确认', priority: 'low', status: 'pending' }
                ];
                renderTodos(fakeTodos);
            }
        })
        .catch(() => {
            // API失败，使用假数据
            const fakeTodos = [
                { id: 1, title: '故障日志处理', priority: 'high', status: 'pending' },
                { id: 2, title: '检修单审核', priority: 'medium', status: 'pending' },
                { id: 3, title: '操作票审核', priority: 'medium', status: 'pending' },
                { id: 4, title: '周计划确认', priority: 'low', status: 'pending' }
            ];
            renderTodos(fakeTodos);
        });
}

/**
 * 渲染待办事项
 */
function renderTodos(todos) {
    const container = document.getElementById('todoContainer');
    if (!container) return;
    
    container.innerHTML = todos.map(todo => `
        <div class="todo-item ${todo.priority}">
            <span class="todo-icon">${todo.priority === 'high' ? '🔴' : todo.priority === 'medium' ? '🟡' : '🟢'}</span>
            <div class="todo-content">
                <div class="todo-title">${todo.title}</div>
            </div>
            <span class="todo-status">${todo.status === 'completed' ? '✓' : '○'}</span>
        </div>
    `).join('');
}

/**
 * 显示计划工作量弹窗
 */
function showPlanWorkloadModal(event) {
    event.preventDefault();
    event.stopPropagation();
    
    // 调用后端API获取数据
    fetch(`${(window.BASE_PATH || '')}/api/plan_workload_detail`)
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
    fetch(`${(window.BASE_PATH || '')}/api/nonplan_workload_detail`)
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
        const response = await fetch(`${(window.BASE_PATH || '')}/api/workload_dashboard`);
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
 * 显示工作量详情弹窗
 * @param {string} type - 'plan' 或 'non-plan'
 */
function showWorkloadModal(type) {
    const modal = document.getElementById('workloadModal');
    const title = document.getElementById('workloadModalTitle');
    const content = document.getElementById('workloadModalContent');
    if (!modal || !content) return;

    // 先显示内容，再异步加载数据
    modal.classList.remove('hidden');

    if (type === 'plan') {
        title.textContent = '📋 计划工作量详情';
        content.innerHTML = `
            <div class="plan-workload-card">
                <div class="plan-card-header"><span class="plan-icon"></span><span class="plan-title">计划检修</span></div>
                <div class="plan-card-body">
                    <div class="plan-sub-row"><span class="plan-sub-label">开展中</span><input type="number" class="plan-sub-input" id="plan-maint-ip" /></div>
                    <div class="plan-sub-row"><span class="plan-sub-label">已终结</span><input type="number" class="plan-sub-input" id="plan-maint-cp" /></div>
                </div>
            </div>
            <div class="plan-workload-card">
                <div class="plan-card-header"><span class="plan-icon">⚡</span><span class="plan-title">转供电</span></div>
                <div class="plan-card-body">
                    <div class="plan-sub-row"><span class="plan-sub-label">开展中</span><input type="number" class="plan-sub-input" id="plan-transfer-ip" /></div>
                    <div class="plan-sub-row"><span class="plan-sub-label">已终结</span><input type="number" class="plan-sub-input" id="plan-transfer-cp" /></div>
                </div>
            </div>
            <div class="plan-workload-card">
                <div class="plan-card-header"><span class="plan-icon">️</span><span class="plan-title">设备投退</span></div>
                <div class="plan-card-body">
                    <div class="plan-sub-row"><span class="plan-sub-label">开展中</span><input type="number" class="plan-sub-input" id="plan-equip-ip" /></div>
                    <div class="plan-sub-row"><span class="plan-sub-label">已终结</span><input type="number" class="plan-sub-input" id="plan-equip-cp" /></div>
                </div>
            </div>
            <div class="plan-workload-card">
                <div class="plan-card-header"><span class="plan-icon"></span><span class="plan-title">周计划</span></div>
                <div class="plan-card-body">
                    <div class="plan-sub-row"><span class="plan-sub-label">开展中</span><input type="number" class="plan-sub-input" id="plan-weekly-ip" /></div>
                    <div class="plan-sub-row"><span class="plan-sub-label">已终结</span><input type="number" class="plan-sub-input" id="plan-weekly-cp" /></div>
                </div>
            </div>
            <div style="grid-column: 1 / -1; display: flex; justify-content: flex-end; margin-top: 16px; gap: 12px;">
                <button class="btn-cancel" onclick="closeWorkloadModal()">取消</button>
                <button class="btn-save" onclick="savePlanWorkload()">保存</button>
            </div>
        `;
        // 异步加载数据
        fetch(`${(window.BASE_PATH || '')}/api/plan_workload_detail`)
            .then(r => r.json())
            .then(data => {
                const d = data.details || {};
                const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? 0; };
                setVal('plan-maint-ip', d.maintenance?.in_progress);
                setVal('plan-maint-cp', d.maintenance?.completed);
                setVal('plan-transfer-ip', d.transfer?.in_progress);
                setVal('plan-transfer-cp', d.transfer?.completed);
                setVal('plan-equip-ip', d.equipment?.in_progress);
                setVal('plan-equip-cp', d.equipment?.completed);
                setVal('plan-weekly-ip', d.weekly_plan?.in_progress);
                setVal('plan-weekly-cp', d.weekly_plan?.completed);
            })
            .catch(() => {});
    } else {
        title.textContent = ' 非计划工作量详情';
        content.innerHTML = `
            <div class="plan-workload-card">
                <div class="plan-card-header"><span class="plan-icon"></span><span class="plan-title">故障日志</span></div>
                <div class="plan-card-body"><div class="plan-sub-row"><span class="plan-sub-label">数量</span><input type="number" class="plan-sub-input" id="np-fault" /></div></div>
            </div>
            <div class="plan-workload-card">
                <div class="plan-card-header"><span class="plan-icon">⚠️</span><span class="plan-title">异常缺陷</span></div>
                <div class="plan-card-body"><div class="plan-sub-row"><span class="plan-sub-label">数量</span><input type="number" class="plan-sub-input" id="np-defect" /></div></div>
            </div>
            <div class="plan-workload-card">
                <div class="plan-card-header"><span class="plan-icon">🔴</span><span class="plan-title">重过载</span></div>
                <div class="plan-card-body"><div class="plan-sub-row"><span class="plan-sub-label">数量</span><input type="number" class="plan-sub-input" id="np-overload" /></div></div>
            </div>
            <div style="grid-column: 1 / -1; display: flex; justify-content: flex-end; margin-top: 16px; gap: 12px;">
                <button class="btn-cancel" onclick="closeWorkloadModal()">取消</button>
                <button class="btn-save" onclick="saveNonPlanWorkload()">保存</button>
            </div>
        `;
        fetch(`${(window.BASE_PATH || '')}/api/nonplan_workload_detail`)
            .then(r => r.json())
            .then(data => {
                const d = data.details || {};
                const el1 = document.getElementById('np-fault');
                const el2 = document.getElementById('np-defect');
                const el3 = document.getElementById('np-overload');
                if (el1) el1.value = d.fault?.count ?? 0;
                if (el2) el2.value = d.defect?.count ?? 0;
                if (el3) el3.value = d.overload?.count ?? 0;
            })
            .catch(() => {});
    }
}

/**
 * 关闭工作量弹窗
 */
function closeWorkloadModal() {
    const modal = document.getElementById('workloadModal');
    if (modal) modal.classList.add('hidden');
}

/**
 * 保存计划工作量
 */
function savePlanWorkload() {
    const data = {
        maintenance: {
            in_progress: parseInt(document.getElementById('plan-maint-ip')?.value || 0),
            completed: parseInt(document.getElementById('plan-maint-cp')?.value || 0)
        },
        transfer: {
            in_progress: parseInt(document.getElementById('plan-transfer-ip')?.value || 0),
            completed: parseInt(document.getElementById('plan-transfer-cp')?.value || 0)
        },
        equipment: {
            in_progress: parseInt(document.getElementById('plan-equip-ip')?.value || 0),
            completed: parseInt(document.getElementById('plan-equip-cp')?.value || 0)
        },
        weekly_plan: {
            in_progress: parseInt(document.getElementById('plan-weekly-ip')?.value || 0),
            completed: parseInt(document.getElementById('plan-weekly-cp')?.value || 0)
        }
    };
    
    fetch(`${(window.BASE_PATH || '')}/api/plan_workload_detail`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            alert('保存成功！');
            closeWorkloadModal();
            // 刷新页面数据
            if (typeof updatePlanDashboardCards === 'function') updatePlanDashboardCards();
        } else {
            alert('保存失败：' + (result.message || '未知错误'));
        }
    })
    .catch(err => {
        alert('保存失败：' + err.message);
    });
}

/**
 * 保存非计划工作量
 */
function saveNonPlanWorkload() {
    const data = {
        fault: { count: parseInt(document.getElementById('np-fault')?.value || 0) },
        defect: { count: parseInt(document.getElementById('np-defect')?.value || 0) },
        overload: { count: parseInt(document.getElementById('np-overload')?.value || 0) }
    };
    
    fetch(`${(window.BASE_PATH || '')}/api/nonplan_workload_detail`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            alert('保存成功！');
            closeWorkloadModal();
            if (typeof updateNonPlanDashboardCards === 'function') updateNonPlanDashboardCards();
        } else {
            alert('保存失败：' + (result.message || '未知错误'));
        }
    })
    .catch(err => {
        alert('保存失败：' + err.message);
    });
}
function showTodoModal() {
    const modal = document.getElementById('todoModal');
    if (!modal) return;
    modal.classList.remove('hidden');
}

function showRiskModal() {
    const modal = document.getElementById('riskModal');
    if (!modal) return;
    modal.classList.remove('hidden');
}

/**
 * 显示知识库弹窗
 */
function showKnowledgeModal() {
    const modal = document.getElementById('knowledgeModal');
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.style.display = '';
}

/**
 * 关闭知识库弹窗
 */
function closeKnowledgeModal() {
    const modal = document.getElementById('knowledgeModal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.style.display = 'none';
}

/**
 * 处理知识库输入框回车事件
 */
function handleInputKeydown(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        // TODO: 实现知识库搜索
    }
}

/**
 * 显示快速操作弹窗
 */
function showQuickActionModal() {
    const modal = document.getElementById('quickActionModal');
    if (!modal) return;
    modal.classList.remove('hidden');
}

/**
 * 关闭快速操作弹窗
 */
function closeQuickActionModal() {
    const modal = document.getElementById('quickActionModal');
    if (!modal) return;
    modal.classList.add('hidden');
}

/**
 * 显示工作量统计弹窗
 */
function showWorkloadStatsModal() {
    const modal = document.getElementById('workloadStatsModal');
    if (!modal) return;
    modal.classList.remove('hidden');
}

/**
 * 关闭工作量统计弹窗
 */
function closeWorkloadStatsModal() {
    const modal = document.getElementById('workloadStatsModal');
    if (!modal) return;
    modal.classList.add('hidden');
}

/**
 * 显示决策报告弹窗
 */
function showDecisionReportModal() {
    const modal = document.getElementById('decisionReportModal');
    if (!modal) return;
    modal.classList.remove('hidden');
}

/**
 * 关闭决策报告弹窗
 */
function closeDecisionReportModal() {
    const modal = document.getElementById('decisionReportModal');
    if (!modal) return;
    modal.classList.add('hidden');
}


// ========== 显示班组详情弹窗 ==========
function showStaffDetail() {
    const modal = document.getElementById('staffModal');
    if (!modal) return;
    
    // Update modal info
    const teamName = document.getElementById('onDutyTeamName')?.textContent || 'A 班';
    const currentStaff = document.getElementById('currentStaff')?.textContent || '--';
    const suggestedStaff = document.getElementById('suggestedStaff')?.textContent || '--';
    const overloadStatus = document.getElementById('overloadStatus')?.textContent || '--';
    
    const modalTeam = document.getElementById('modalOnDutyTeam');
    if (modalTeam) modalTeam.textContent = teamName;
    
    // 立即显示弹窗，不等待数据加载
    modal.classList.remove('hidden');
    
    // 异步加载班组详情（不阻塞弹窗显示）
    const today = new Date().toISOString().split('T')[0];
    fetch(`${(window.BASE_PATH || '')}/api/staff/detail?team_name=${encodeURIComponent(teamName)}&date_str=${today}`)
        .then(r => r.json())
        .then(data => {
            console.log('Staff detail loaded:', data);
            if (data.success && data.data) {
                renderStaffDetail(data.data);
            }
        })
        .catch(err => {
            console.error('Failed to load staff detail:', err);
        });
}

/**
 * 渲染值班人员详情
 */
function renderStaffDetail(data) {
    // 更新弹窗头部信息
    const modalTeam = document.getElementById('modalOnDutyTeam');
    if (modalTeam) modalTeam.textContent = data.on_duty_team_name || 'A 班';
    
    // 找到当前班组的当值人员
    const currentTeam = data.teams?.find(t => t.team_name === data.on_duty_team_name);
    const onDutyPersonnel = currentTeam?.on_duty_personnel || [];
    const restingPersonnel = data.resting_personnel || [];
    
    // 更新人数统计
    const onDutyCount = document.getElementById('onDutyCount');
    if (onDutyCount) onDutyCount.textContent = onDutyPersonnel.length + '人';
    
    const restingCount = document.getElementById('restingCount');
    if (restingCount) restingCount.textContent = restingPersonnel.length + '人';
    
    // 渲染当值人员列表
    const onDutyList = document.getElementById('onDutyStaffList');
    if (onDutyList) {
        onDutyList.innerHTML = onDutyPersonnel.map(p => `
            <div class="staff-card">
                <div class="staff-avatar">${p.name.charAt(0)}</div>
                <div class="staff-info">
                    <div class="staff-name">${p.name}</div>
                    <div class="staff-role">${p.role} ${p.team}</div>
                </div>
            </div>
        `).join('');
    }
    
    // 渲染休息人员列表（带加入当值按钮）
    const restingList = document.getElementById('restingStaffList');
    if (restingList) {
        restingList.innerHTML = restingPersonnel.map(p => `
            <div class="staff-card">
                <div class="staff-avatar">${p.name.charAt(0)}</div>
                <div class="staff-info">
                    <div class="staff-name">${p.name}</div>
                    <div class="staff-role">${p.role} ${p.team}</div>
                </div>
                <button class="btn-join-duty" onclick="joinDuty('${p.id}', '${p.name}', '${p.team}')">加入当值</button>
            </div>
        `).join('');
    }
}

/**
 * 加入当值
 */
async function joinDuty(personId, personName, homeTeamName) {
    try {
        const response = await fetch(`${(window.BASE_PATH || '')}/api/staff/temp/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                record_id: '',
                person_id: personId,
                person_name: personName,
                home_team_name: homeTeamName
            })
        });
        const result = await response.json();
        if (result.success) {
            alert(`${personName} 已成功加入当值`);
            // 重新加载数据
            const teamName = document.getElementById('onDutyTeamName')?.textContent || 'A 班';
            const today = new Date().toISOString().split('T')[0];
            const data = await fetch(`${(window.BASE_PATH || '')}/api/staff/detail?team_name=${encodeURIComponent(teamName)}&date_str=${today}`).then(r => r.json());
            if (data.success && data.data) {
                renderStaffDetail(data.data);
            }
        } else {
            alert('加入失败：' + (result.error || '未知错误'));
        }
    } catch (err) {
        alert('加入失败：' + err.message);
    }
}

