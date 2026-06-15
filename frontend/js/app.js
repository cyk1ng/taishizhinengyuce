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
        
        // 追加内容，同时过滤掉 <tool_call> 标签（流式传输时实时清理）
        const currentText = contentDiv.innerText || '';
        const rawText = currentText + content;
        // 1. 移除完整的 <tool_call>...</tool_call> 块
        // 2. 移除末尾未闭合的 <tool_call>... 部分
        const filteredText = rawText
            .replace(/<tool_call>[\s\S]*?<\/tool_call>/g, '')
            .replace(/<tool_call>[\s\S]*$/gm, '')
            .trim();
        contentDiv.innerHTML = md.render(filteredText);
        
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
        // 发送请求给后端获取数据
        const response = await fetch(`${window.location.origin}/api/workload_dashboard`);
        
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
    
    // 更新人员当量
    const avgCapacity = hourlyDetails.reduce((sum, h) => sum + (h.staff_capacity || 0), 0) / 24 || 0;
    document.getElementById('staffCapacity').textContent = avgCapacity.toFixed(1);
    
    // 更新超负荷状态
    const overloadEl = document.getElementById('overloadStatus');
    overloadEl.textContent = overloadCount > 0 ? '是' : '否';
    overloadEl.className = 'staff-value ' + (overloadCount > 0 ? 'warning' : 'success');
    
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
        const response = await fetch('/api/weather');
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
    
    // 获取当前日期的工作量数据
    const today = new Date().toISOString().split('T')[0];
    
    // 调用后端API获取数据
    // 这里暂时使用假数据
    const planData = {
        maintenance: {
            in_progress: 8,
            completed: 3,
            total: 11
        },
        transfer: {
            in_progress: 5,
            completed: 2,
            total: 7
        },
        equipment: {
            in_progress: 4,
            completed: 1,
            total: 5
        },
        weekly_plan: {
            in_progress: 12,
            completed: 6,
            total: 18
        },
        shift_allocation: {
            morning: 15,
            afternoon: 20,
            night: 6
        }
    };
    
    // 更新弹窗数据
    updatePlanWorkloadModal(planData);
    
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
    document.getElementById('plan-maintenance-in-progress').textContent = data.maintenance.in_progress;
    document.getElementById('plan-maintenance-completed').textContent = data.maintenance.completed;
    document.getElementById('plan-maintenance-total').textContent = data.maintenance.total;
    
    // 更新转供电
    document.getElementById('plan-transfer-in-progress').textContent = data.transfer.in_progress;
    document.getElementById('plan-transfer-completed').textContent = data.transfer.completed;
    document.getElementById('plan-transfer-total').textContent = data.transfer.total;
    
    // 更新设备投退
    document.getElementById('plan-equipment-in-progress').textContent = data.equipment.in_progress;
    document.getElementById('plan-equipment-completed').textContent = data.equipment.completed;
    document.getElementById('plan-equipment-total').textContent = data.equipment.total;
    
    // 更新周计划
    document.getElementById('plan-weekly-in-progress').textContent = data.weekly_plan.in_progress;
    document.getElementById('plan-weekly-completed').textContent = data.weekly_plan.completed;
    document.getElementById('plan-weekly-total').textContent = data.weekly_plan.total;
    
    // 更新班次分配
    document.getElementById('shift-morning-count').textContent = data.shift_allocation.morning;
    document.getElementById('shift-afternoon-count').textContent = data.shift_allocation.afternoon;
    document.getElementById('shift-night-count').textContent = data.shift_allocation.night;
}

/**
 * 显示非计划工作量弹窗
 */
function showNonPlanWorkloadModal(event) {
    event.preventDefault();
    event.stopPropagation();
    
    // 获取当前日期的工作量数据
    const today = new Date().toISOString().split('T')[0];
    
    // 调用后端API获取数据
    // 这里暂时使用假数据
    const nonPlanData = {
        fault: {
            count: 8
        },
        defect: {
            count: 5
        },
        overload: {
            count: 2
        },
        total: 15
    };
    
    // 更新弹窗数据
    updateNonPlanWorkloadModal(nonPlanData);
    
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
    document.getElementById('non-plan-fault-count').textContent = data.fault.count;
    
    // 更新异常缺陷
    document.getElementById('non-plan-defect-count').textContent = data.defect.count;
    
    // 更新重过载
    document.getElementById('non-plan-overload-count').textContent = data.overload.count;
    
    // 更新总计
    document.getElementById('non-plan-total-count').textContent = data.total;
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
        const response = await fetch(`${window.location.origin}/api/workload_dashboard`);
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
