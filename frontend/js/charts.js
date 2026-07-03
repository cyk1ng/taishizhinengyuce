/**
 * SVG 图表渲染（替代 Chart.js）
 * 配网调度智能预测系统 - 深蓝科技感主题
 * 零外部依赖，纯 SVG 矢量图
 */

// ============================================================
// 颜色主题
// ============================================================
const chartColors = {
    primary: '#3b82f6', secondary: '#06b6d4', cyan: '#22d3ee',
    green: '#10b981', yellow: '#f59e0b', orange: '#f97316',
    red: '#ef4444', purple: '#8b5cf6', pink: '#ec4899', gray: '#64748b',
    darkBg: '#0a1628', cardBg: '#0f1e33',
    text: '#8ba3c7', textBright: '#b8d0f0', gridLine: 'rgba(30, 58, 95, 0.5)'
};
const chartColorsList = ['#3b82f6','#06b6d4','#22d3ee','#10b981','#f59e0b','#f97316','#ef4444','#8b5cf6','#ec4899','#64748b'];
const SVG_NS = 'http://www.w3.org/2000/svg';

function _svg(tag, attrs) {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
    return el;
}
function _text(content, x, y, attrs) {
    const t = _svg('text', { x: '' + x, y: '' + y, fill: chartColors.text, ...attrs });
    t.textContent = '' + (content ?? '');
    return t;
}
function _makeSVG(w, h) {
    const s = _svg('svg', { width: '100%', height: '100%', viewBox: `0 0 ${w} ${h}` });
    s.style.display = 'block';
    return s;
}

// ============================================================
// SVG 柱状图
// ============================================================
function _drawBars(svg, ox, oy, w, h, bars, opts) {
    const maxVal = opts.maxValue || Math.max(...bars.map(b => b.value || 0), 1);
    const barW = opts.barWidth || Math.min(24, w / bars.length * 0.5);
    const gap = Math.max(1, (w - barW * bars.length) / (bars.length + 1));
    bars.forEach(function(bar, i) {
        const bx = ox + gap + i * (barW + gap);
        const bh = bar.value > 0 ? Math.max(2, (bar.value / maxVal) * h) : 0;
        const color = bar.color || chartColorsList[i % chartColorsList.length];
        svg.appendChild(_svg('rect', { x: '' + bx, y: '' + (oy + h - bh), width: '' + barW, height: '' + bh, fill: color, rx: '3', ry: '3' }));
        svg.appendChild(_text(bar.label || '', bx + barW / 2, oy + h + 13, { 'text-anchor': 'middle', 'font-size': '9' }));
        if (bh > 16) svg.appendChild(_text('' + bar.value, bx + barW / 2, oy + h - bh - 4, { 'text-anchor': 'middle', 'font-size': '9', 'font-weight': 'bold', fill: chartColors.textBright }));
    });
}

// ============================================================
// SVG 环形图（doughnut）
// ============================================================
function _drawDoughnut(svg, cx, cy, r, segments, holeRatio) {
    holeRatio = holeRatio || 0.6;
    const circ = 2 * Math.PI * r;
    const total = segments.reduce(function(s, seg) { return s + (seg.value || 0); }, 0);
    const sw = r * (1 - holeRatio) * 2;
    if (total === 0) {
        svg.appendChild(_svg('circle', { cx: '' + cx, cy: '' + cy, r: '' + r, fill: 'none', stroke: chartColors.gridLine, 'stroke-width': '' + sw }));
        svg.appendChild(_text('0', cx, cy + 1, { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': '' + Math.max(12, r * 0.4), 'font-weight': 'bold', fill: chartColors.textBright }));
        return;
    }
    var offset = 0;
    segments.forEach(function(seg) {
        if (!seg.value) return;
        var ratio = seg.value / total;
        var len = ratio * circ;
        svg.appendChild(_svg('circle', { cx: '' + cx, cy: '' + cy, r: '' + r, fill: 'none', stroke: seg.color || chartColors.primary, 'stroke-width': '' + sw, 'stroke-dasharray': len + ' ' + circ, 'stroke-dashoffset': '' + (-offset), transform: 'rotate(-90 ' + cx + ' ' + cy + ')' }));
        offset += len;
    });
    svg.appendChild(_text('' + total, cx, cy + 1, { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': '' + Math.max(12, r * 0.4), 'font-weight': 'bold', fill: chartColors.textBright }));
}
function _doughnutLegendHtml(segments) {
    var h = '<div style="display:flex;flex-direction:column;gap:4px;">';
    segments.forEach(function(seg) {
        h += '<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:#8ba3c7;"><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:' + (seg.color || '#3b82f6') + ';flex-shrink:0;"></span><span>' + (seg.label || '') + '</span><span style="margin-left:auto;font-weight:bold;color:#b8d0f0;">' + (seg.value ?? 0) + '</span></div>';
    });
    h += '</div>';
    return h;
}

// ============================================================
// SVG 折线/曲线图（用于时间轴）
// ============================================================
function _drawLineChart(svg, ox, oy, w, h, points, color, opts) {
    if (!points || !points.length) return;
    var maxVal = opts.maxValue || Math.max.apply(null, points.map(function(p) { return p.value || 0; })) || 1;
    var minVal = opts.minValue || 0;
    var range = maxVal - minVal || 1;
    var stepX = w / (points.length - 1);
    // Grid
    for (var i = 0; i <= 4; i++) {
        var gy = oy + h * i / 4;
        svg.appendChild(_svg('line', { x1: '' + ox, y1: '' + gy, x2: '' + (ox + w), y2: '' + gy, stroke: chartColors.gridLine, 'stroke-width': '0.5' }));
    }
    // Points
    var coords = points.map(function(p, i) {
        var px = ox + i * stepX;
        var py = oy + h - ((p.value - minVal) / range) * h;
        return px + ',' + py;
    });
    svg.appendChild(_svg('polyline', { points: coords.join(' '), fill: 'none', stroke: color || chartColors.primary, 'stroke-width': '2', 'stroke-linejoin': 'round' }));
    // Area fill
    var area = [ox + ',' + (oy + h)].concat(coords).concat([(ox + w) + ',' + (oy + h)]);
    svg.appendChild(_svg('polygon', { points: area.join(' '), fill: color || chartColors.primary, opacity: '0.1' }));
}

// ============================================================
// 图表实例变量
// ============================================================
var moduleBusinessChart = null;
var ticketChart = null;
var workloadTimelineChart = null;
var networkOrderChart = null;
var _lastWorkloadData = null;

// ============================================================
// 模块业务分布 - 柱状图
// ============================================================
function initModuleBusinessChart(data) {
    var el = document.getElementById('moduleBusinessChart');
    if (!el) return;
    var def = { labels: ['周计划','设备投退','跳闸','缺陷','重过载','保供电','检修业务','方式单'], values: [0,0,0,0,0,0,0,0] };
    var d = data || def;
    el.innerHTML = '';
    var svg = _makeSVG(300, 180);
    var bars = d.labels.map(function(l, i) { return { label: l, value: d.values[i] || 0, color: chartColorsList[i % chartColorsList.length] }; });
    _drawBars(svg, 30, 10, 250, 130, bars, {});
    el.appendChild(svg);
}

// ============================================================
// 故障/缺陷分布 - 环形图
// ============================================================
function initTicketChart(data) {
    var el = document.getElementById('ticketChart');
    if (!el) return;
    var def = { labels: ['周计划','设备投退','缺陷','保供电'], values: [0,0,0,0] };
    var d = data || def;
    var segs = d.labels.map(function(l, i) { return { label: l, value: d.values[i] || 0, color: chartColorsList[i % chartColorsList.length] }; });
    el.innerHTML = '';
    var wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;align-items:center;gap:12px;height:100%;padding:8px;';
    var svg = _makeSVG(130, 130);
    _drawDoughnut(svg, 65, 65, 50, segs, 0.65);
    wrap.appendChild(svg);
    var legend = document.createElement('div');
    legend.style.cssText = 'flex:1;min-width:0;';
    legend.innerHTML = _doughnutLegendHtml(segs);
    wrap.appendChild(legend);
    el.appendChild(wrap);
}

// ============================================================
// 工作量时间轴 - 折线图
// ============================================================
function initWorkloadTimelineChart(data) {
    var el = document.getElementById('workloadTimelineChart');
    if (!el) return;
    var points = data && data.length > 0 ? data : [];
    for (var i = points.length; i < 24; i++) {
        points.push({ label: i + ':00', value: 0 });
    }
    el.innerHTML = '';
    var svg = _makeSVG(800, 180);
    _drawLineChart(svg, 40, 10, 720, 130, points, chartColors.cyan, {});
    // Hour labels
    var stepX = 720 / 23;
    for (var i = 0; i < 24; i += 3) {
        svg.appendChild(_text(points[i].label, 40 + i * stepX, 175, { 'text-anchor': 'middle', 'font-size': '8' }));
    }
    el.appendChild(svg);
}

// ============================================================
// 网架订单分布 - 环形图
// ============================================================
function initNetworkOrderChart(data) {
    var el = document.getElementById('networkOrderChart');
    if (!el) return;
    var def = { labels: ['重过载','跳闸','操作票','其他'], values: [0,0,0,0] };
    var d = data || def;
    var segs = d.labels.map(function(l, i) { return { label: l, value: d.values[i] || 0, color: chartColorsList[i % chartColorsList.length] }; });
    el.innerHTML = '';
    var wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;align-items:center;gap:12px;height:100%;padding:8px;';
    var svg = _makeSVG(130, 130);
    _drawDoughnut(svg, 65, 65, 50, segs, 0.6);
    wrap.appendChild(svg);
    var legend = document.createElement('div');
    legend.style.cssText = 'flex:1;min-width:0;';
    legend.innerHTML = _doughnutLegendHtml(segs);
    wrap.appendChild(legend);
    el.appendChild(wrap);
}

// ============================================================
// 初始化所有图表
// ============================================================
function initAllCharts() {
    initModuleBusinessChart();
    initTicketChart();
    initWorkloadTimelineChart();
    initNetworkOrderChart();
}

// ============================================================
// 更新工作量数据（由 app.js 调用）
// ============================================================
function updateWorkloadData(data) {
    if (!data) return;
    _lastWorkloadData = data;
    
    // 解析 hourly_details 生成图表数据
    var hourly = data.hourly_details || [];
    
    // 1. 模块业务分布
    var summary = data.summary || {};
    var bizData = {
        labels: ['周计划','设备投退','跳闸','缺陷','重过载','保供电','检修业务','方式单'],
        values: [
            summary.weekly_plan_count || 0,
            summary.equipment_count || 0,
            summary.trip_count || 0,
            summary.defect_count || 0,
            summary.overload_count || 0,
            summary.protect_supply_count || 0,
            summary.maintenance_count || 0,
            summary.transfer_count || 0
        ]
    };
    initModuleBusinessChart(bizData);
    
    // 2. 故障/缺陷分布
    var faultData = {
        labels: ['周计划','设备投退','缺陷','保供电'],
        values: [
            summary.weekly_plan_count || 0,
            summary.equipment_count || 0,
            summary.defect_count || 0,
            summary.protect_supply_count || 0
        ]
    };
    initTicketChart(faultData);
    
    // 3. 时间轴
    var timelineData = [];
    var planMap = {};
    (hourly || []).forEach(function(h) {
        planMap[h.hour] = (h.plan_count || 0) + (h.fault_count || 0);
    });
    for (var i = 0; i < 24; i++) {
        timelineData.push({ label: i + ':00', value: planMap[i] || 0 });
    }
    initWorkloadTimelineChart(timelineData);
    
    // 4. 网架订单
    var orderData = {
        labels: ['重过载','跳闸','操作票','其他'],
        values: [
            summary.overload_count || 0,
            summary.trip_count || 0,
            summary.operation_ticket_count || 0,
            Math.max(0, (summary.total_plan_count || 0) - (summary.overload_count || 0) - (summary.trip_count || 0) - (summary.operation_ticket_count || 0))
        ]
    };
    initNetworkOrderChart(orderData);
}

// ============================================================
// 人员配置条状图（用于弹窗内）
// ============================================================
function createStaffingChart(containerId, data) {
    var el = document.getElementById(containerId);
    if (!el) return;
    if (!data || !data.labels) {
        el.innerHTML = '<div style="color:#5a7a9e;text-align:center;padding:20px;font-size:12px;">暂无数据</div>';
        return;
    }
    var bars = data.labels.map(function(l, i) {
        return { label: l, value: data.values[i] || 0, color: data.colors ? data.colors[i] : chartColorsList[i % chartColorsList.length] };
    });
    el.innerHTML = '';
    var svg = _makeSVG(Math.max(200, bars.length * 40), 150);
    _drawBars(svg, 20, 10, Math.max(160, bars.length * 36), 110, bars, {});
    el.appendChild(svg);
}

// ============================================================
// 风险仪表盘（环形进度）
// ============================================================
function createRiskGauge(containerId, value) {
    var el = document.getElementById(containerId);
    if (!el) return;
    value = Math.max(0, Math.min(100, value || 0));
    var color = value < 30 ? chartColors.green : value < 60 ? chartColors.yellow : chartColors.red;
    el.innerHTML = '';
    var wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;';
    var svg = _makeSVG(100, 100);
    _drawDoughnut(svg, 50, 50, 38, [{ label: '风险', value: value, color: color }, { label: '', value: 100 - value, color: chartColors.gridLine }], 0.6);
    wrap.appendChild(svg);
    var lbl = document.createElement('div');
    lbl.style.cssText = 'color:#5a7a9e;font-size:10px;margin-top:4px;';
    lbl.textContent = value > 60 ? '高风险' : value > 30 ? '中风险' : '低风险';
    wrap.appendChild(lbl);
    el.appendChild(wrap);
}// ============================================================
// 弹窗和编辑功能
// ============================================================

/**
 * 打开弹窗
 */
function openModal(modalId) {
    try {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
        } else {
            console.error('找不到弹窗元素:', modalId);
        }
    } catch (error) {
        console.error('打开弹窗错误:', error);
    }
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
 * 编辑天气信息
 */
function editWeather() {
    try {
        // 从天气显示卡片读取当前数据
        const weatherTempDisplayEl = document.getElementById('weatherTempDisplay');
        const weatherPrecipDisplayEl = document.getElementById('weatherPrecipDisplay');
        const weatherWindDisplayEl = document.getElementById('weatherWindDisplay');
        const weatherExtremeDisplayEl = document.getElementById('weatherExtremeDisplay');

        if (weatherTempDisplayEl && weatherPrecipDisplayEl && weatherWindDisplayEl) {
            // 从显示卡片提取数据
            const tempText = weatherTempDisplayEl.textContent || '';
            const tempMatch = tempText.match(/(\d+)~(\d+)/);
            const tempMin = tempMatch ? tempMatch[1] : '25';
            const tempMax = tempMatch ? tempMatch[2] : '35';

            const precipText = weatherPrecipDisplayEl.textContent || '降水量: 小';
            const precipitation = precipText.replace('降水量: ', '').trim();

            const windText = weatherWindDisplayEl.textContent || '风力: 小';
            const wind = windText.replace('风力: ', '').trim();

            const extreme = (weatherExtremeDisplayEl && !weatherExtremeDisplayEl.classList.contains('hidden')) ?
                weatherExtremeDisplayEl.textContent.replace('⚠️ ', '').trim() : '';

            // 填充到编辑弹窗
            const tempMinEl = document.getElementById('weatherTempMin');
            const tempMaxEl = document.getElementById('weatherTempMax');
            const precipEl = document.getElementById('weatherPrecipitation');
            const windEl = document.getElementById('weatherWind');
            const extremeEl = document.getElementById('weatherExtreme');

            if (tempMinEl) tempMinEl.value = tempMin;
            if (tempMaxEl) tempMaxEl.value = tempMax;
            if (precipEl) precipEl.value = precipitation;
            if (windEl) windEl.value = wind;
            if (extremeEl) extremeEl.value = extreme;
        } else {
            console.warn('天气显示卡片不存在，使用默认值');
            // 使用默认值
            const tempMinEl = document.getElementById('weatherTempMin');
            const tempMaxEl = document.getElementById('weatherTempMax');
            const precipEl = document.getElementById('weatherPrecipitation');
            const windEl = document.getElementById('weatherWind');
            const extremeEl = document.getElementById('weatherExtreme');

            if (tempMinEl) tempMinEl.value = 25;
            if (tempMaxEl) tempMaxEl.value = 35;
            if (precipEl) precipEl.value = '小';
            if (windEl) windEl.value = '小';
            if (extremeEl) extremeEl.value = '';
        }

        openModal('weatherModal');
    } catch (error) {
        console.error('编辑天气信息错误:', error);
        alert('编辑天气信息失败，请稍后重试');
    }
}

/**
 * 根据月份自动填充天气数据
 */
function autoFillWeather() {
    try {
        const monthSelect = document.getElementById('weatherMonth');
        const month = parseInt(monthSelect.value);

        if (!month) {
            alert('请选择月份');
            return;
        }

        // 根据月份设置典型的天气数据
        const weatherData = {
            1: { tempMin: 5, tempMax: 15, precipitation: '小', wind: '中', extreme: '寒潮' },  // 1月：冬季，寒冷
            2: { tempMin: 8, tempMax: 18, precipitation: '小', wind: '中', extreme: '' },     // 2月：冬季末，稍回暖
            3: { tempMin: 12, tempMax: 22, precipitation: '小', wind: '小', extreme: '' },   // 3月：春季，温和
            4: { tempMin: 16, tempMax: 26, precipitation: '中', wind: '小', extreme: '' },   // 4月：春季，开始多雨
            5: { tempMin: 20, tempMax: 30, precipitation: '中', wind: '小', extreme: '' },   // 5月：春末，温暖
            6: { tempMin: 25, tempMax: 35, precipitation: '大', wind: '中', extreme: '暴雨' }, // 6月：雨季开始
            7: { tempMin: 26, tempMax: 36, precipitation: '大', wind: '中', extreme: '暴雨' }, // 7月：雨季高峰
            8: { tempMin: 25, tempMax: 35, precipitation: '大', wind: '中', extreme: '雷雨' }, // 8月：雨季，高温
            9: { tempMin: 20, tempMax: 30, precipitation: '中', wind: '小', extreme: '' },   // 9月：秋季，凉爽
            10: { tempMin: 15, tempMax: 25, precipitation: '小', wind: '小', extreme: '' },  // 10月：秋季，干燥
            11: { tempMin: 10, tempMax: 20, precipitation: '小', wind: '中', extreme: '寒潮' }, // 11月：初冬
            12: { tempMin: 5, tempMax: 15, precipitation: '小', wind: '中', extreme: '寒潮' }  // 12月：冬季
        };

        const data = weatherData[month];

        const tempMinEl = document.getElementById('weatherTempMin');
        const tempMaxEl = document.getElementById('weatherTempMax');
        const precipEl = document.getElementById('weatherPrecipitation');
        const windEl = document.getElementById('weatherWind');
        const extremeEl = document.getElementById('weatherExtreme');

        if (tempMinEl) tempMinEl.value = data.tempMin;
        if (tempMaxEl) tempMaxEl.value = data.tempMax;
        if (precipEl) precipEl.value = data.precipitation;
        if (windEl) windEl.value = data.wind;
        if (extremeEl) extremeEl.value = data.extreme;

        console.log(`已自动填充${month}月的天气数据:`, data);
    } catch (error) {
        console.error('自动填充天气数据错误:', error);
        alert('自动填充天气数据失败，请稍后重试');
    }
}

/**
 * 保存天气信息
 */
function saveWeather() {
    try {
        const tempMinEl = document.getElementById('weatherTempMin');
        const tempMaxEl = document.getElementById('weatherTempMax');
        const precipEl = document.getElementById('weatherPrecipitation');
        const windEl = document.getElementById('weatherWind');
        const extremeEl = document.getElementById('weatherExtreme');

        if (!tempMinEl || !tempMaxEl || !precipEl || !windEl || !extremeEl) {
            console.error('找不到天气输入框');
            alert('保存失败，请刷新页面后重试');
            return;
        }

        const tempMin = tempMinEl.value || 25;
        const tempMax = tempMaxEl.value || 35;
        const precipitation = precipEl.value || '小';
        const wind = windEl.value || '小';
        const extreme = extremeEl.value || '';

        // 验证温度范围
        if (parseInt(tempMin) > parseInt(tempMax)) {
            alert('最低温度不能大于最高温度');
            return;
        }

        // 构建显示文本
        let displayText = `${tempMin}~${tempMax}℃ ${precipitation} ${wind}`;
        if (extreme) {
            displayText += ` ${extreme}`;
        }

        // 更新天气显示卡片
        const weatherTempDisplayEl = document.getElementById('weatherTempDisplay');
        const weatherPrecipDisplayEl = document.getElementById('weatherPrecipDisplay');
        const weatherWindDisplayEl = document.getElementById('weatherWindDisplay');
        const weatherExtremeDisplayEl = document.getElementById('weatherExtremeDisplay');

        if (weatherTempDisplayEl) {
            weatherTempDisplayEl.innerHTML = `${tempMin}~${tempMax}<span class="unit">℃</span>`;
        }
        if (weatherPrecipDisplayEl) {
            weatherPrecipDisplayEl.textContent = `降水量: ${precipitation}`;
        }
        if (weatherWindDisplayEl) {
            weatherWindDisplayEl.textContent = `风力: ${wind}`;
        }
        if (weatherExtremeDisplayEl) {
            if (extreme) {
                weatherExtremeDisplayEl.textContent = `⚠️ ${extreme}`;
                weatherExtremeDisplayEl.classList.add('show');
            } else {
                weatherExtremeDisplayEl.classList.remove('show');
            }
        }

        closeModal('weatherModal');

        // 调用后端API保存数据
        fetch('/api/weather', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tempMin: tempMin,
                tempMax: tempMax,
                precipitation: precipitation,
                wind: wind,
                extreme: extreme
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('天气信息保存成功:', data);
                alert('天气信息保存成功');
            } else {
                console.error('天气信息保存失败:', data.error);
                alert('天气信息保存失败: ' + (data.error || '未知错误'));
            }
        })
        .catch(error => {
            console.error('天气信息保存错误:', error);
            alert('天气信息保存失败，请稍后重试');
        });

        console.log('保存天气信息:', {
            tempMin,
            tempMax,
            precipitation,
            wind,
            extreme
        });
    } catch (error) {
        console.error('保存天气信息错误:', error);
        alert('保存天气信息失败，请稍后重试');
    }
}

/**
 * 编辑计划工作量
 */
function editPlannedWorkload(event) {
    try {
        event.stopPropagation();

        // 获取当前值
        const totalEl = document.getElementById('stat-weekly-plan');
        const ongoingEl = document.getElementById('stat-weekly-ongoing');
        const doneEl = document.getElementById('stat-weekly-done');

        if (!totalEl || !ongoingEl || !doneEl) {
            console.error('找不到计划工作量元素');
            alert('无法编辑计划工作量，请刷新页面后重试');
            return;
        }

        // 提取数字（处理可能包含单位的情况）
        const totalText = totalEl.textContent || totalEl.innerText || '0';
        const ongoingText = ongoingEl.textContent || ongoingEl.innerText || '0';
        const doneText = doneEl.textContent || doneEl.innerText || '0';

        const totalVal = parseInt(totalText.replace(/[^\d-]/g, '')) || 0;
        const ongoingVal = parseInt(ongoingText.replace(/[^\d-]/g, '')) || 0;
        const doneVal = parseInt(doneText.replace(/[^\d-]/g, '')) || 0;

        const plannedTotalEl = document.getElementById('plannedTotal');
        const plannedOngoingEl = document.getElementById('plannedOngoing');
        const plannedDoneEl = document.getElementById('plannedDone');

        if (plannedTotalEl) plannedTotalEl.value = totalVal;
        if (plannedOngoingEl) plannedOngoingEl.value = ongoingVal;
        if (plannedDoneEl) plannedDoneEl.value = doneVal;

        openModal('plannedModal');
    } catch (error) {
        console.error('编辑计划工作量错误:', error);
        alert('编辑计划工作量失败，请稍后重试');
    }
}

/**
 * 保存计划工作量
 */
function savePlannedWorkload() {
    try {
        const totalEl = document.getElementById('plannedTotal');
        const ongoingEl = document.getElementById('plannedOngoing');
        const doneEl = document.getElementById('plannedDone');

        if (!totalEl || !ongoingEl || !doneEl) {
            console.error('找不到计划工作量输入框');
            alert('保存失败，请刷新页面后重试');
            return;
        }

        const total = totalEl.value || 0;
        const ongoing = ongoingEl.value || 0;
        const done = doneEl.value || 0;

        // 更新显示
        const statPlanEl = document.getElementById('stat-weekly-plan');
        const statOngoingEl = document.getElementById('stat-weekly-ongoing');
        const statDoneEl = document.getElementById('stat-weekly-done');

        if (statPlanEl) statPlanEl.innerHTML = `${total}<span class="unit">单</span>`;
        if (statOngoingEl) statOngoingEl.textContent = ongoing;
        if (statDoneEl) statDoneEl.textContent = done;

        closeModal('plannedModal');

        // 这里可以调用后端API保存数据
        console.log('保存计划工作量:', { total, ongoing, done });
    } catch (error) {
        console.error('保存计划工作量错误:', error);
        alert('保存计划工作量失败，请稍后重试');
    }
}

/**
 * 编辑非计划工作量
 */
function editUnplannedWorkload(event) {
    try {
        event.stopPropagation();

        // 获取当前值
        const totalEl = document.getElementById('stat-trip');
        const successEl = document.getElementById('stat-trip-success');
        const failEl = document.getElementById('stat-trip-fail');

        if (!totalEl || !successEl || !failEl) {
            console.error('找不到非计划工作量元素');
            alert('无法编辑非计划工作量，请刷新页面后重试');
            return;
        }

        // 提取数字（处理可能包含单位的情况）
        const totalText = totalEl.textContent || totalEl.innerText || '0';
        const successText = successEl.textContent || successEl.innerText || '0';
        const failText = failEl.textContent || failEl.innerText || '0';

        const totalVal = parseInt(totalText.replace(/[^\d-]/g, '')) || 0;
        const successVal = parseInt(successText.replace(/[^\d-]/g, '')) || 0;
        const failVal = parseInt(failText.replace(/[^\d-]/g, '')) || 0;

        const unplannedTotalEl = document.getElementById('unplannedTotal');
        const unplannedSuccessEl = document.getElementById('unplannedSuccess');
        const unplannedFailEl = document.getElementById('unplannedFail');

        if (unplannedTotalEl) unplannedTotalEl.value = totalVal;
        if (unplannedSuccessEl) unplannedSuccessEl.value = successVal;
        if (unplannedFailEl) unplannedFailEl.value = failVal;

        openModal('unplannedModal');
    } catch (error) {
        console.error('编辑非计划工作量错误:', error);
        alert('编辑非计划工作量失败，请稍后重试');
    }
}

/**
 * 保存非计划工作量
 */
function saveUnplannedWorkload() {
    try {
        const totalEl = document.getElementById('unplannedTotal');
        const successEl = document.getElementById('unplannedSuccess');
        const failEl = document.getElementById('unplannedFail');

        if (!totalEl || !successEl || !failEl) {
            console.error('找不到非计划工作量输入框');
            alert('保存失败，请刷新页面后重试');
            return;
        }

        const total = totalEl.value || 0;
        const success = successEl.value || 0;
        const fail = failEl.value || 0;

        // 更新显示
        const statTripEl = document.getElementById('stat-trip');
        const statSuccessEl = document.getElementById('stat-trip-success');
        const statFailEl = document.getElementById('stat-trip-fail');

        if (statTripEl) statTripEl.innerHTML = `${total}<span class="unit">起</span>`;
        if (statSuccessEl) statSuccessEl.textContent = success;
        if (statFailEl) statFailEl.textContent = fail;

        closeModal('unplannedModal');

        // 这里可以调用后端API保存数据
        console.log('保存非计划工作量:', { total, success, fail });
    } catch (error) {
        console.error('保存非计划工作量错误:', error);
        alert('保存非计划工作量失败，请稍后重试');
    }
}

/**
 * 显示时间段详情
 */
/**
 * 当前编辑的时间段索引
 */
let currentTimeSlotIndex = null;

function showTimeSlotDetail(index, chartData) {
    try {
        // 保存当前编辑的时间段索引
        currentTimeSlotIndex = index;

        // 获取当前时间段和下一时间段
        const currentHour = index;
        const nextHour = (index + 1) % 24;

        const currentTime = `${currentHour.toString()}:00`;
        const nextTime = `${nextHour.toString()}:00`;

        // 更新弹窗内容
        document.getElementById('timeSlotTime').textContent = `${currentTime}-${nextTime}`;

        // 当值人员数量（从总当量中取整）
        const totalWorkload = chartData.workloadTotal[index];
        const staffCount = Math.ceil(totalWorkload);
        document.getElementById('timeSlotTotal').textContent = staffCount;

        // 班组人员工作量
        document.getElementById('timeSlotCapacity').value = chartData.staffCapacity[index].toFixed(1);

        // 气象预警等级（如果数据中有，则设置，否则保持默认）
        if (chartData.weatherWarningLevel && chartData.weatherWarningLevel[index]) {
            document.getElementById('weatherWarningLevel').value = chartData.weatherWarningLevel[index];
        } else {
            document.getElementById('weatherWarningLevel').value = '';
        }

        openModal('timeSlotModal');
    } catch (error) {
        console.error('显示时间段详情错误:', error);
        alert('显示时间段详情失败: ' + error.message);
    }
}

/**
 * 保存时间段配置
 */
function saveTimeSlotConfig() {
    try {
        if (currentTimeSlotIndex === null) {
            alert('未选择时间段');
            return;
        }

        // 获取表单数据
        const capacity = parseFloat(document.getElementById('timeSlotCapacity').value) || 0;
        const warningLevel = document.getElementById('weatherWarningLevel').value;

        // 这里可以调用后端API保存数据
        console.log('保存时间段配置:', {
            index: currentTimeSlotIndex,
            capacity: capacity,
            warningLevel: warningLevel
        });

        // 关闭弹窗
        closeModal('timeSlotModal');

        // 显示成功提示
        alert('配置保存成功！');
    } catch (error) {
        console.error('保存配置错误:', error);
        alert('保存配置失败: ' + error.message);
    }
}

/**
 * 获取班次时段
 */
function getShiftPeriod(hour) {
    if (hour >= 6 && hour < 12) {
        return '早班 (08:00-16:00)';
    } else if (hour >= 12 && hour < 20) {
        return '中班 (16:00-24:00)';
    } else {
        return '晚班 (00:00-08:00)';
    }
}

// ========================================
// 值班人员管理
// ========================================

// 当前选中的班组
let currentTeam = 'A班';
let currentShift = null;

// 班次配置
const SHIFT_DEFS = {
    '早班': { label: '早班', time: '08:00-16:00', color: '#ff9800' },
    '中班': { label: '中班', time: '16:00-24:00', color: '#2196f3' },
    '晚班': { label: '晚班', time: '00:00-08:00', color: '#9c27b0' }
};

// 当前值班数据（由后端 API 加载，失败时自动降级为假数据）
let staffState = {
    date: '',
    teams: [],        // 各班组值班详情
    restingPersonnel: [],  // 休息人员列表
    restingCount: 0,
    loaded: false,
    isFallback: false   // 是否使用了降级假数据
};

/**
 * 降级假数据（后端不可用时自动使用）
 */
const FALLBACK_STAFF_DATA = {
    on_duty_team_name: 'A班',
    teams: [
        {
            record_id: 'fallback_A',
            team_name: 'A班', shift_type: '早班',
            schedule_status: 'Y',
            on_duty_time: '08:00', off_duty_time: '16:00',
            on_duty_count: 11,
            on_duty_personnel: [
                { id: 'U001', name: '宗德文', role: '值班长', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U101', name: '王云', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U102', name: '晏清阳', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U103', name: '杨凡奇', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U104', name: '李浩', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U105', name: '王玥', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U106', name: '何静', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U107', name: '李光临', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U108', name: '李杰', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U109', name: '杨宏敏', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' },
                { id: 'U110', name: '龚瑞泉', role: '值班人员', team: 'A班', type: 'core', status: 'on-duty' }
            ]
        },
        {
            record_id: 'fallback_B',
            team_name: 'B班', shift_type: '中班',
            schedule_status: 'N',
            on_duty_time: '16:00', off_duty_time: '24:00',
            on_duty_count: 7,
            on_duty_personnel: [
                { id: 'U002', name: '朱利明', role: '值班长', team: 'B班', type: 'core', status: 'on-duty' },
                { id: 'U201', name: '张小丽', role: '值班人员', team: 'B班', type: 'core', status: 'on-duty' },
                { id: 'U202', name: '王海东', role: '值班人员', team: 'B班', type: 'core', status: 'on-duty' },
                { id: 'U203', name: '马兴源', role: '值班人员', team: 'B班', type: 'core', status: 'on-duty' },
                { id: 'U204', name: '杨智翔', role: '值班人员', team: 'B班', type: 'core', status: 'on-duty' },
                { id: 'U205', name: '丁紫签', role: '值班人员', team: 'B班', type: 'core', status: 'on-duty' },
                { id: 'U206', name: '康林春', role: '值班人员', team: 'B班', type: 'core', status: 'on-duty' }
            ]
        },
        {
            record_id: 'fallback_C',
            team_name: 'C班', shift_type: '晚班',
            schedule_status: 'N',
            on_duty_time: '00:00', off_duty_time: '08:00',
            on_duty_count: 8,
            on_duty_personnel: [
                { id: 'U003', name: '余永胜', role: '值班长', team: 'C班', type: 'core', status: 'on-duty' },
                { id: 'U301', name: '王品', role: '值班人员', team: 'C班', type: 'core', status: 'on-duty' },
                { id: 'U302', name: '高恩福', role: '值班人员', team: 'C班', type: 'core', status: 'on-duty' },
                { id: 'U303', name: '杨志芳', role: '值班人员', team: 'C班', type: 'core', status: 'on-duty' },
                { id: 'U304', name: '沙成石', role: '值班人员', team: 'C班', type: 'core', status: 'on-duty' },
                { id: 'U305', name: '王一格', role: '值班人员', team: 'C班', type: 'core', status: 'on-duty' },
                { id: 'U306', name: '黄佳', role: '值班人员', team: 'C班', type: 'core', status: 'on-duty' },
                { id: 'U307', name: '耿绍胜', role: '值班人员', team: 'C班', type: 'core', status: 'on-duty' }
            ]
        },
        {
            record_id: 'fallback_D',
            team_name: 'D值', shift_type: '',
            schedule_status: 'N',
            on_duty_time: '', off_duty_time: '',
            on_duty_count: 9,
            on_duty_personnel: [
                { id: 'U004', name: '韦于成', role: '值班长', team: 'D值', type: 'core', status: 'on-duty' },
                { id: 'U401', name: '王祥伟', role: '值班人员', team: 'D值', type: 'core', status: 'on-duty' },
                { id: 'U402', name: '潘伟', role: '值班人员', team: 'D值', type: 'core', status: 'on-duty' },
                { id: 'U403', name: '李云川', role: '值班人员', team: 'D值', type: 'core', status: 'on-duty' },
                { id: 'U404', name: '保文鸿', role: '值班人员', team: 'D值', type: 'core', status: 'on-duty' },
                { id: 'U405', name: '杨丽丽', role: '值班人员', team: 'D值', type: 'core', status: 'on-duty' },
                { id: 'U406', name: '陶胜晟', role: '值班人员', team: 'D值', type: 'core', status: 'on-duty' },
                { id: 'U407', name: '张小丽', role: '值班人员', team: 'D值', type: 'core', status: 'on-duty' },
                { id: 'U408', name: '黄佳', role: '值班人员', team: 'D值', type: 'core', status: 'on-duty' }
            ]
        },
        {
            record_id: 'fallback_E',
            team_name: 'E班', shift_type: '',
            schedule_status: 'N',
            on_duty_time: '', off_duty_time: '',
            on_duty_count: 7,
            on_duty_personnel: [
                { id: 'U005', name: '王勇', role: '值班长', team: 'E班', type: 'core', status: 'on-duty' },
                { id: 'U501', name: '欧钰瞧', role: '值班人员', team: 'E班', type: 'core', status: 'on-duty' },
                { id: 'U502', name: '李燚', role: '值班人员', team: 'E班', type: 'core', status: 'on-duty' },
                { id: 'U503', name: '孙榕华', role: '值班人员', team: 'E班', type: 'core', status: 'on-duty' },
                { id: 'U504', name: '张梅', role: '值班人员', team: 'E班', type: 'core', status: 'on-duty' },
                { id: 'U505', name: '黑晓捷', role: '值班人员', team: 'E班', type: 'core', status: 'on-duty' },
                { id: 'U506', name: '宋静', role: '值班人员', team: 'E班', type: 'core', status: 'on-duty' }
            ]
        }
    ],
    restingPersonnel: [
        { id: 'U002', name: '朱利明', role: '值班长', team: 'B班', status: 'rest' },
        { id: 'U201', name: '张小丽', role: '值班人员', team: 'B班', status: 'rest' },
        { id: 'U202', name: '王海东', role: '值班人员', team: 'B班', status: 'rest' },
        { id: 'U203', name: '马兴源', role: '值班人员', team: 'B班', status: 'rest' },
        { id: 'U204', name: '杨智翔', role: '值班人员', team: 'B班', status: 'rest' },
        { id: 'U205', name: '丁紫签', role: '值班人员', team: 'B班', status: 'rest' },
        { id: 'U206', name: '康林春', role: '值班人员', team: 'B班', status: 'rest' },
        { id: 'U003', name: '余永胜', role: '值班长', team: 'C班', status: 'rest' },
        { id: 'U301', name: '王品', role: '值班人员', team: 'C班', status: 'rest' },
        { id: 'U302', name: '高恩福', role: '值班人员', team: 'C班', status: 'rest' },
        { id: 'U303', name: '杨志芳', role: '值班人员', team: 'C班', status: 'rest' },
        { id: 'U304', name: '沙成石', role: '值班人员', team: 'C班', status: 'rest' },
        { id: 'U305', name: '王一格', role: '值班人员', team: 'C班', status: 'rest' },
        { id: 'U306', name: '黄佳', role: '值班人员', team: 'C班', status: 'rest' },
        { id: 'U307', name: '耿绍胜', role: '值班人员', team: 'C班', status: 'rest' },
        { id: 'U004', name: '韦于成', role: '值班长', team: 'D值', status: 'rest' },
        { id: 'U401', name: '王祥伟', role: '值班人员', team: 'D值', status: 'rest' },
        { id: 'U402', name: '潘伟', role: '值班人员', team: 'D值', status: 'rest' },
        { id: 'U403', name: '李云川', role: '值班人员', team: 'D值', status: 'rest' },
        { id: 'U404', name: '保文鸿', role: '值班人员', team: 'D值', status: 'rest' },
        { id: 'U405', name: '杨丽丽', role: '值班人员', team: 'D值', status: 'rest' },
        { id: 'U406', name: '陶胜晟', role: '值班人员', team: 'D值', status: 'rest' },
        { id: 'U407', name: '张小丽', role: '值班人员', team: 'D值', status: 'rest' },
        { id: 'U408', name: '黄佳', role: '值班人员', team: 'D值', status: 'rest' },
        { id: 'U005', name: '王勇', role: '值班长', team: 'E班', status: 'rest' },
        { id: 'U501', name: '欧钰瞧', role: '值班人员', team: 'E班', status: 'rest' },
        { id: 'U502', name: '李燚', role: '值班人员', team: 'E班', status: 'rest' },
        { id: 'U503', name: '孙榕华', role: '值班人员', team: 'E班', status: 'rest' },
        { id: 'U504', name: '张梅', role: '值班人员', team: 'E班', status: 'rest' },
        { id: 'U505', name: '黑晓捷', role: '值班人员', team: 'E班', status: 'rest' },
        { id: 'U506', name: '宋静', role: '值班人员', team: 'E班', status: 'rest' }
    ]
};/**
 * 从后端加载值班人员数据
 * 如果后端不可用，自动降级使用假数据
 */
async function loadStaffData(teamName = '') {
    try {
        const dateStr = new Date().toISOString().slice(0, 10);
        const url = `/api/staff/detail?team_name=${encodeURIComponent(teamName)}&date_str=${dateStr}`;
        const resp = await fetch(url);
        const result = await resp.json();
        if (result.success && result.data && result.data.teams && result.data.teams.length > 0) {
            staffState.date = result.data.date || dateStr;
            staffState.teams = result.data.teams || [];
            staffState.onDutyTeamName = result.data.on_duty_team_name || '';
            staffState.restingPersonnel = result.data.resting_personnel || [];
            staffState.restingCount = result.data.resting_count || 0;
            staffState.loaded = true;
            staffState.isFallback = false;
            // 数据加载完成后，按班次自动选中班组并渲染
            filterTeamsByShift();
            return;
        }
        // API 返回成功但无数据，使用降级
        console.warn('后端数据为空，使用降级假数据');
        applyFallbackData();
    } catch (e) {
        console.warn('后端不可用，使用降级假数据:', e.message);
        applyFallbackData();
    }
    // 降级数据：按班次自动选中班组并渲染
    filterTeamsByShift();
}

/**
 * 应用降级假数据
 */
function applyFallbackData() {
    staffState.date = new Date().toISOString().slice(0, 10);
    staffState.teams = FALLBACK_STAFF_DATA.teams.map(t => ({
        ...t,
        on_duty_personnel: [...t.on_duty_personnel]
    }));
    staffState.onDutyTeamName = FALLBACK_STAFF_DATA.on_duty_team_name || 'A班';
    staffState.restingPersonnel = [...FALLBACK_STAFF_DATA.restingPersonnel];
    staffState.restingCount = staffState.restingPersonnel.length;
    staffState.loaded = true;
    staffState.isFallback = true;
}

/**
 * 根据当前时间获取默认班次
 */
function getDefaultShiftByTime() {
    const hour = new Date().getHours();
    if (hour >= 0 && hour < 8) return '晚班';
    if (hour >= 8 && hour < 16) return '早班';
    return '中班';
}

/**
 * 显示值班人员详情弹窗
 */
async function showStaffDetail() {
    // 根据当前时间自动选中对应班次
    const defaultShift = getDefaultShiftByTime();
    currentShift = defaultShift;
    document.querySelectorAll('.shift-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.shift === defaultShift);
    });
    
    await loadStaffData(currentTeam);
    
    // 更新当值班组信息栏
    updateOnDutyInfoBar();
    
    // filterTeamsByShift 已经在 loadStaffData 里调用
    // renderStaffList 也在 loadStaffData 里调用
    openModal('staffModal');
}

/**
 * 更新弹窗中的信息栏
 * 显示当前选中的班组信息
 */
function updateOnDutyInfoBar() {
    const teamEl = document.getElementById('modalOnDutyTeam');
    const timeEl = document.getElementById('modalOnDutyTime');
    const shiftEl = document.getElementById('modalOnDutyShift');
    if (!teamEl || !timeEl || !shiftEl) return;
    
    const teams = staffState.teams || [];
    // 根据当前选中的班组显示信息
    const targetTeam = teams.find(t => t.team_name === currentTeam);
    
    if (targetTeam) {
        teamEl.textContent = targetTeam.team_name || '--';
        const timeText = targetTeam.on_duty_time && targetTeam.off_duty_time
            ? `${targetTeam.on_duty_time} - ${targetTeam.off_duty_time}`
            : '--';
        timeEl.textContent = timeText;
        shiftEl.textContent = targetTeam.shift_type || '--';
    } else {
        teamEl.textContent = currentTeam || '--';
        timeEl.textContent = '--';
        shiftEl.textContent = '未排班';
    }
    
    // 更新班次按钮上的时间标签
    updateShiftButtonTimes();
}

/**
 * 更新班次按钮上的时间显示
 * 优先使用数据中的时间，没有数据时使用默认时间
 */
function updateShiftButtonTimes() {
    const teams = staffState.teams || [];
    const shiftTimeMap = {};
    
    // 默认班次时间（当数据中缺少时使用）
    const DEFAULT_SHIFT_TIMES = {
        '晚班': '00:00-08:00',
        '早班': '08:00-16:00',
        '中班': '16:00-24:00'
    };
    
    // 从数据中收集时间
    teams.forEach(t => {
        if (t.shift_type && !shiftTimeMap[t.shift_type]) {
            const timeStr = t.on_duty_time && t.off_duty_time
                ? `${t.on_duty_time}-${t.off_duty_time}`
                : '';
            shiftTimeMap[t.shift_type] = timeStr;
        }
    });
    
    // 更新按钮文本
    document.querySelectorAll('.shift-btn').forEach(btn => {
        const shift = btn.dataset.shift;
        // 优先使用数据中的时间，没有则用默认时间
        const timeStr = shiftTimeMap[shift] || DEFAULT_SHIFT_TIMES[shift] || '';
        const icons = { '晚班': '🌙', '早班': '☀️', '中班': '🌆' };
        const icon = icons[shift] || '';
        btn.textContent = timeStr ? `${icon} ${shift} ${timeStr}` : `${icon} ${shift}`;
    });
}

/**
 * 选择班组
 * 同时联动更新班次选中状态（双向联动）
 */
async function selectTeam(team) {
    // 统一补全班组名称：'A'/'B'/'C'/'E' -> 'A班'/'B班'/'C班'/'E班'
    // 'D值' 已经是完整名称，无需补全
    if (!team.endsWith('班') && !team.endsWith('值')) {
        team = team + '班';
    }
    currentTeam = team;
    
    // 更新班组按钮样式
    document.querySelectorAll('.team-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.team === team.replace('班', '')) {
            btn.classList.add('active');
        }
    });
    
    // ── 反向联动：根据班组查找班次，更新班次选中状态 ──
    const teams = staffState.teams || [];
    const teamData = teams.find(t => t.team_name === team);
    const matchedShift = teamData ? teamData.shift_type : null;
    
    if (matchedShift) {
        // 该班组有排班 → 自动选中对应班次
        currentShift = matchedShift;
        document.querySelectorAll('.shift-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.shift === currentShift);
        });
    } else {
        // 该班组无排班 → 取消所有班次选中
        currentShift = null;
        document.querySelectorAll('.shift-btn').forEach(btn => {
            btn.classList.remove('active');
        });
    }
    
    // 更新信息栏
    updateOnDutyInfoBar();
    
    // 重新渲染人员列表
    renderStaffList();
}

/**
 * 选择班次
 */
function selectShift(shiftKey) {
    // 点击相同班次 = 取消选中（显示全部）
    if (currentShift === shiftKey) {
        currentShift = null;
    } else {
        currentShift = shiftKey;
    }
    
    // 更新班次按钮样式
    document.querySelectorAll('.shift-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.shift === currentShift);
    });
    
    // 根据班次自动选中对应班组
    filterTeamsByShift();
    // 更新信息栏
    updateOnDutyInfoBar();
}

/**
 * 根据选中的班次自动选中对应班组
 * 所有班组按钮始终显示，班次只影响自动选中
 */
function filterTeamsByShift() {
    const allTeamBtns = document.querySelectorAll('.team-btn');
    
    // 所有班组按钮始终显示（不移除hidden）
    allTeamBtns.forEach(btn => btn.classList.remove('hidden'));
    
    if (!currentShift) return;
    
    // 查找当前班次对应的班组并自动选中
    const teams = staffState.teams || [];
    const shiftTeam = teams.find(t => t.shift_type === currentShift);
    if (shiftTeam) {
        const teamKey = shiftTeam.team_name.replace('班', '');
        // 自动选中对应班组
        selectTeam(teamKey);
    }
}


function getCurrentOnDutyTeam() {
    if (!staffState.teams || staffState.teams.length === 0) return null;
    // 按当前时间确定当值班次
    const currentShiftName = getDefaultShiftByTime();
    // 查找分配到这个班次的班组
    const match = staffState.teams.find(t => t.shift_type === currentShiftName);
    return match || null;
}

/**
 * 渲染人员列表
 */
function renderStaffList() {
    const onDutyList = document.getElementById('onDutyStaffList');
    const restingList = document.getElementById('restingStaffList');
    const onDutyCount = document.getElementById('onDutyCount');
    const restingCount = document.getElementById('restingCount');
    
    if (!onDutyList || !restingList) return;
    
    // 按当前时间找到当值班组
    const dutyTeam = getCurrentOnDutyTeam();
    const isOnDutyTeam = dutyTeam && dutyTeam.team_name === currentTeam;
    
    let onDutyStaff, restingStaff;
    
    if (isOnDutyTeam) {
        // 选中的班组就是当值班组 → 当值人员=本班组，休息人员=所有其他班组
        onDutyStaff = dutyTeam ? (dutyTeam.on_duty_personnel || []) : [];
        const onDutyIds = new Set(onDutyStaff.map(p => p.id));
        
        restingStaff = [];
        (staffState.teams || []).forEach(team => {
            const teamStaff = team.on_duty_personnel || [];
            teamStaff.forEach(p => {
                if (!onDutyIds.has(p.id)) {
                    restingStaff.push(p);
                }
            });
        });
        (staffState.restingPersonnel || []).forEach(p => {
            if (!onDutyIds.has(p.id) && !restingStaff.find(r => r.id === p.id)) {
                restingStaff.push(p);
            }
        });
    } else {
        // 选中的班组不是当值班组 → 当值人员为空，休息人员=选中班组的人
        onDutyStaff = [];
        const selectedTeamData = (staffState.teams || []).find(t => t.team_name === currentTeam);
        restingStaff = selectedTeamData ? [...(selectedTeamData.on_duty_personnel || [])] : [];
        // 也加上专门的休息人员列表中属于选中班组的人
        (staffState.restingPersonnel || []).forEach(p => {
            if (p.team === currentTeam && !restingStaff.find(r => r.id === p.id)) {
                restingStaff.push(p);
            }
        });
    }
    
    // 更新数量
    if (onDutyCount) onDutyCount.textContent = `${onDutyStaff.length}人`;
    if (restingCount) restingCount.textContent = `${restingStaff.length}人`;
    
    // 渲染当值人员
    onDutyList.innerHTML = onDutyStaff.map(staff => createStaffCard(staff, 'on-duty')).join('');
    
    // 渲染休息人员
    restingList.innerHTML = restingStaff.map(staff => createStaffCard(staff, 'rest')).join('');
}

/**
 * 创建人员卡片HTML
 */
function createStaffCard(staff, type) {
    const isActive = staff.status === 'on-duty';
    const activeClass = isActive ? 'active' : 'inactive';
    
    // 角色显示
    const roleLabel = staff.role || '值班人员';
    const roleLevelMap = { '值班长': 3, '值班人员': 2, '临时值班人员': 1 };
    const roleLevel = roleLevelMap[staff.role] || 0;
    
    // 所属班组标签
    const teamLabel = staff.team || '';
    
    let actionButtons = '';
    if (type === 'on-duty' && staff.type === 'temp') {
        // 临时借调人员：显示"设为休息"按钮
        const dutyTeam = getCurrentOnDutyTeam();
        actionButtons = `
            <div class="staff-actions">
                <button class="staff-action-btn rest-btn" onclick="setStaffRest('${staff.id}')">设为休息</button>
            </div>
        `;
    } else if (type === 'rest') {
        // 休息人员：显示"加入当值"按钮
        const dutyTeam = getCurrentOnDutyTeam();
        actionButtons = `
            <div class="staff-actions">
                <button class="staff-action-btn duty-btn" onclick="setStaffOnDuty('${staff.id}', '${staff.name}', '${teamLabel}')">加入当值</button>
            </div>
        `;
    }
    
    return `
        <div class="staff-card ${activeClass}">
            <div class="staff-avatar">👨‍💼</div>
            <div class="staff-info">
                <div class="staff-name">${staff.name}</div>
                <div class="staff-role">${roleLabel}</div>
                <div class="staff-badges">
                    ${roleLevel > 0 ? `<span class="badge role-${roleLevel}">${roleLabel}</span>` : ''}
                    ${teamLabel ? `<span class="badge team-badge">${teamLabel}</span>` : ''}
                    ${staff.type === 'temp' ? '<span class="badge">临时</span>' : ''}
                    ${!isActive ? '<span class="badge">休息中</span>' : ''}
                </div>
            </div>
            ${actionButtons}
        </div>
    `;
}

/**
 * 设置人员为休息（移除临时借调）
 */
async function setStaffRest(personId) {
    const dutyTeam = getCurrentOnDutyTeam();
    if (!dutyTeam || !dutyTeam.record_id) { alert('未找到当前值班记录'); return; }
    // 降级模式或API失败：本地操作
    if (staffState.isFallback) {
        const idx = dutyTeam.on_duty_personnel.findIndex(p => p.id === personId && p.type === 'temp');
        if (idx !== -1) {
            const removed = dutyTeam.on_duty_personnel.splice(idx, 1)[0];
            staffState.restingPersonnel.push({ id: removed.id, name: removed.name, role: removed.role, team: removed.team, status: 'rest' });
            dutyTeam.on_duty_count = dutyTeam.on_duty_personnel.length;
            staffState.restingCount = staffState.restingPersonnel.length;
            renderStaffList();
        }
        return;
    }
    try {
        const resp = await fetch('/api/staff/temp/remove', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ record_id: dutyTeam.record_id, person_id: personId })
        });
        const result = await resp.json();
        if (result.success) { await loadStaffData(currentTeam); renderStaffList(); }
        else { alert('操作失败: ' + (result.error || result.msg || '')); }
    } catch (e) {
        console.error('设为休息失败，降级本地操作:', e);
        const idx = dutyTeam.on_duty_personnel.findIndex(p => p.id === personId && p.type === 'temp');
        if (idx !== -1) {
            const removed = dutyTeam.on_duty_personnel.splice(idx, 1)[0];
            staffState.restingPersonnel.push({ id: removed.id, name: removed.name, role: removed.role, team: removed.team, status: 'rest' });
            dutyTeam.on_duty_count = dutyTeam.on_duty_personnel.length;
            staffState.restingCount = staffState.restingPersonnel.length;
            renderStaffList();
        }
    }
}

/**
 * 设置人员为当值（跨班组临时借调）
 */
async function setStaffOnDuty(personId, personName, homeTeamName) {
    const dutyTeam = getCurrentOnDutyTeam();
    if (!dutyTeam || !dutyTeam.record_id) { alert('未找到当前值班记录'); return; }
    // 降级模式：本地操作
    if (staffState.isFallback) {
        const idx = staffState.restingPersonnel.findIndex(p => p.id === personId);
        if (idx === -1) return;
        const moved = staffState.restingPersonnel.splice(idx, 1)[0];
        dutyTeam.on_duty_personnel.push({ id: moved.id, name: moved.name, role: '临时值班人员', team: moved.team, type: 'temp', status: 'on-duty' });
        dutyTeam.on_duty_count = dutyTeam.on_duty_personnel.length;
        staffState.restingCount = staffState.restingPersonnel.length;
        renderStaffList();
        return;
    }
    try {
        const resp = await fetch('/api/staff/temp/add', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ record_id: dutyTeam.record_id, person_id: personId, person_name: personName, home_team_name: homeTeamName })
        });
        const result = await resp.json();
        if (result.success) { await loadStaffData(currentTeam); renderStaffList(); }
        else { alert('操作失败: ' + (result.error || result.msg || '')); }
    } catch (e) {
        console.error('加入当值失败，降级本地操作:', e);
        const idx = staffState.restingPersonnel.findIndex(p => p.id === personId);
        if (idx === -1) return;
        const moved = staffState.restingPersonnel.splice(idx, 1)[0];
        dutyTeam.on_duty_personnel.push({ id: moved.id, name: moved.name, role: '临时值班人员', team: moved.team, type: 'temp', status: 'on-duty' });
        dutyTeam.on_duty_count = dutyTeam.on_duty_personnel.length;
        staffState.restingCount = staffState.restingPersonnel.length;
        renderStaffList();
    }
}

// 页面加载完成后初始化图表
document.addEventListener('DOMContentLoaded', function() {
    initAllCharts();
    // 异步加载人员数据（首次加载时初始化，后续由用户点击触发）
    loadStaffData(currentTeam).then(() => {
        renderStaffList();
    });
});

/**
 * ========================================
 * 工作量弹窗编辑功能
 * ========================================
 */

/**
 * 双击编辑字段值 - 将数字变为可编辑输入框
 */
window.editFieldValue = function(el) {
    if (el.classList.contains('editing')) return;
    
    const currentValue = el.textContent.trim();
    if (isNaN(parseInt(currentValue))) return;
    
    el.classList.add('editing');
    el.contentEditable = true;
    el.focus();
    
    const range = document.createRange();
    range.selectNodeContents(el);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    
    const finishEdit = function() {
        el.contentEditable = false;
        el.classList.remove('editing');
        el.removeEventListener('blur', finishEdit);
        el.removeEventListener('keydown', onKeyDown);
        
        const card = el.closest('.editable-card');
        if (card) {
            const totalEl = card.querySelector('.field-total');
            if (totalEl) {
                const inProgEl = card.querySelector('.field-value[data-field="in_progress"]');
                const complEl = card.querySelector('.field-value[data-field="completed"]');
                const inProg = parseInt(inProgEl ? inProgEl.textContent : '0');
                const compl = parseInt(complEl ? complEl.textContent : '0');
                totalEl.textContent = inProg + compl;
            }
        }
    };
    
    const onKeyDown = function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            el.blur();
            return;
        }
        if (e.key === 'Escape') {
            el.textContent = currentValue;
            el.blur();
            return;
        }
    };
    
    el.addEventListener('blur', finishEdit);
    el.addEventListener('keydown', onKeyDown);
};

/**
 * 收集弹窗中某个类型的所有编辑数据
 */
function collectOverrideData(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return {};
    
    const data = {};
    const cards = modal.querySelectorAll('.editable-card');
    cards.forEach(card => {
        const category = card.dataset.category;
        if (!category) return;
        data[category] = {};
        card.querySelectorAll('.field-value').forEach(el => {
            const field = el.dataset.field;
            if (field) {
                data[category][field] = parseInt(el.textContent.trim()) || 0;
            }
        });
    });
    return data;
}

/**
 * 保存计划工作量覆盖数据到后端
 */
window.savePlanWorkloadOverride = function() {
    const data = collectOverrideData('planWorkloadModal');
    if (Object.keys(data).length === 0) {
        alert('没有数据可保存');
        return;
    }
    
    const today = new Date().toISOString().slice(0, 10);
    const payload = {
        workload_type: 'plan',
        data: data,
        target_date: today
    };
    
    const btn = document.querySelector('#planWorkloadModal .modal-btn.primary');
    const originalText = btn.textContent;
    btn.textContent = '⏳ 保存中...';
    btn.disabled = true;
    
    fetch('/api/save_workload_override', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(result => {
        if (result.success) {
            updatePlanDashboardCards(data);
            btn.textContent = '✅ 已保存';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 2000);
            showToast('计划工作量已保存', 'success');
        } else {
            btn.textContent = '❌ 保存失败';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 2000);
            showToast('保存失败: ' + (result.error || '未知错误'), 'error');
        }
    })
    .catch(err => {
        console.error('保存失败:', err);
        btn.textContent = '❌ 保存失败';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
        showToast('网络错误，请重试', 'error');
    });
};

/**
 * 保存非计划工作量覆盖数据到后端
 */
window.saveNonPlanWorkloadOverride = function() {
    const data = collectOverrideData('nonPlanWorkloadModal');
    if (Object.keys(data).length === 0) {
        alert('没有数据可保存');
        return;
    }
    
    const today = new Date().toISOString().slice(0, 10);
    const payload = {
        workload_type: 'nonplan',
        data: data,
        target_date: today
    };
    
    const btn = document.querySelector('#nonPlanWorkloadModal .modal-btn.primary');
    const originalText = btn.textContent;
    btn.textContent = '⏳ 保存中...';
    btn.disabled = true;
    
    fetch('/api/save_workload_override', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(result => {
        if (result.success) {
            updateNonPlanDashboardCards(data);
            btn.textContent = '✅ 已保存';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 2000);
            showToast('非计划工作量已保存', 'success');
        } else {
            btn.textContent = '❌ 保存失败';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 2000);
            showToast('保存失败: ' + (result.error || '未知错误'), 'error');
        }
    })
    .catch(err => {
        console.error('保存失败:', err);
        btn.textContent = '❌ 保存失败';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
        showToast('网络错误，请重试', 'error');
    });
};

/**
 * 更新计划工作量的 dashboard 卡片数值
 */
function updatePlanDashboardCards(data) {
    let totalInProgress = 0, totalCompleted = 0;
    Object.values(data).forEach(item => {
        totalInProgress += item.in_progress || 0;
        totalCompleted += item.completed || 0;
    });
    
    const planCard = document.querySelector('.alert-card[data-type="plan-workload"]');
    if (planCard) {
        const values = planCard.querySelectorAll('.alert-value');
        if (values.length >= 3) {
            values[0].textContent = totalInProgress;
            values[1].textContent = totalCompleted;
        }
    }
    
    if (typeof updateCharts === 'function') {
        updateCharts();
    }
}

/**
 * 更新非计划工作量的 dashboard 卡片数值
 */
function updateNonPlanDashboardCards(data) {
    let total = 0;
    Object.values(data).forEach(item => {
        total += item.count || 0;
    });
    
    const nonPlanCard = document.querySelector('.alert-card[data-type="nonplan-workload"]');
    if (nonPlanCard) {
        const value = nonPlanCard.querySelector('.alert-value');
        if (value) {
            value.textContent = total;
        }
    }
    
    if (typeof updateCharts === 'function') {
        updateCharts();
    }
}

/**
 * 简单的 Toast 提示
 */
function showToast(message, type) {
    const existing = document.querySelector('.workload-toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = 'workload-toast';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed; bottom: 24px; right: 24px; z-index: 10000;
        padding: 12px 24px; border-radius: 8px; font-size: 14px; font-weight: 600;
        background: ${type === 'success' ? 'rgba(34,197,94,0.9)' : 'rgba(239,68,68,0.9)'};
        color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: opacity 0.3s ease;
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * ========================================
 * 工作量数据更新检测 & 智能预测
 * ========================================
 */

/**
 * 页面加载时检查工作量数据是否有更新
 * 使用原生 confirm() 提示用户
 */
function checkWorkloadUpdates() {
    const today = new Date().toISOString().slice(0, 10);
    fetch('/api/check_workload_updates?target_date=' + today)
        .then(res => res.json())
        .then(result => {
            if (result.success && result.has_updates) {
                // 使用原生 confirm 弹窗
                const userConfirmed = confirm('检测到工作量源数据有变化，是否用新数据覆盖当前已修改数据？\n\n点击"确定"覆盖更新，点击"取消"保留当前修改。');
                
                if (userConfirmed) {
                    // 用户选择覆盖更新
                    fetch('/api/apply_workload_updates', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({target_date: today})
                    })
                    .then(res => res.json())
                    .then(applyResult => {
                        if (applyResult.success) {
                            showToast('✅ 工作量数据已覆盖更新', 'success');
                            if (typeof refreshData === 'function') {
                                refreshData();
                            } else {
                                location.reload();
                            }
                        } else {
                            showToast('更新失败: ' + (applyResult.error || '未知错误'), 'error');
                        }
                    })
                    .catch(err => {
                        console.error('更新失败:', err);
                        showToast('网络错误，请重试', 'error');
                    });
                } else {
                    showToast('已保留当前修改数据', 'info');
                }
            }
        })
        .catch(err => console.warn('检测工作量更新失败:', err));
}

// 姓名模糊搜索 - 过滤当值/休息人员卡片
function filterStaffList(side) {
    const input = document.getElementById(side === 'on-duty' ? 'onDutySearch' : 'restingSearch');
    const list = document.getElementById(side === 'on-duty' ? 'onDutyList' : 'restingList');
    if (!input || !list) return;
    const keyword = input.value.trim().toLowerCase();
    const cards = list.querySelectorAll('.staff-card');
    cards.forEach(card => {
        const name = card.querySelector('.staff-name');
        if (!name) return;
        const match = !keyword || name.textContent.toLowerCase().includes(keyword);
        card.style.display = match ? '' : 'none';
    });
}

// 页面加载完成后检查工作量更新 - 集成到现有 DOMContentLoaded 中
// 注意: 现有 charts.js 在文件开头已有 DOMContentLoaded 监听，此处通过延迟调用触发
setTimeout(checkWorkloadUpdates, 1500);
