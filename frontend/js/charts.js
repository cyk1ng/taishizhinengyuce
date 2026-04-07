/**
 * Chart.js 配置与初始化
 * 配网调度智能预测系统 - 深蓝科技感主题
 */

// 图表全局配置 - 深蓝主题
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif';
Chart.defaults.color = '#8ba3c7';
Chart.defaults.borderColor = 'rgba(30, 58, 95, 0.5)';

// 颜色主题 - 深蓝科技感
const chartColors = {
    primary: '#3b82f6',
    secondary: '#06b6d4',
    cyan: '#22d3ee',
    green: '#10b981',
    yellow: '#f59e0b',
    orange: '#f97316',
    red: '#ef4444',
    purple: '#8b5cf6',
    pink: '#ec4899',
    gray: '#64748b',
    // 背景色
    gridColor: 'rgba(30, 58, 95, 0.3)',
    tooltipBg: '#152238',
    tooltipText: '#e8f1ff',
    tooltipBorder: '#2563eb'
};

// 图表实例
let moduleBusinessChart = null;
let ticketChart = null;
let networkOrderChart = null;
let workloadTimelineChart = null;

/**
 * 初始化各模块业务情况图表（柱状图，更紧凑）
 */
function initModuleBusinessChart(data = null) {
    const ctx = document.getElementById('moduleBusinessChart');
    if (!ctx) return;
    
    if (moduleBusinessChart) {
        moduleBusinessChart.destroy();
    }
    
    // 空数据（无模拟数据）
    const defaultData = {
        labels: ['周计划', '设备投退', '跳闸', '缺陷', '重过载', '保供电', '检修业务', '方式单'],
        values: [0, 0, 0, 0, 0, 0, 0, 0]
    };
    
    const chartData = data || defaultData;
    
    moduleBusinessChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: '业务数量',
                data: chartData.values,
                backgroundColor: [
                    'rgba(6, 182, 212, 0.7)',
                    'rgba(59, 130, 246, 0.7)',
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(245, 158, 11, 0.7)',
                    'rgba(139, 92, 246, 0.7)',
                    'rgba(16, 185, 129, 0.7)',
                    'rgba(6, 182, 212, 0.7)',
                    'rgba(59, 130, 246, 0.7)'
                ],
                borderColor: [
                    'rgba(6, 182, 212, 1)',
                    'rgba(59, 130, 246, 1)',
                    'rgba(239, 68, 68, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(139, 92, 246, 1)',
                    'rgba(16, 185, 129, 1)',
                    'rgba(6, 182, 212, 1)',
                    'rgba(59, 130, 246, 1)'
                ],
                borderWidth: 1,
                borderRadius: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipText,
                    bodyColor: chartColors.tooltipText,
                    borderColor: chartColors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 4,
                    padding: 8,
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed.y}单`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#5a7a9e', font: { size: 10 } }
                },
                y: {
                    beginAtZero: true,
                    max: 30,
                    grid: { color: chartColors.gridColor, drawBorder: false },
                    ticks: { color: '#5a7a9e', font: { size: 10 }, stepSize: 10 }
                }
            }
        }
    });
}

/**
 * 初始化操作票情况图表（饼图）
 */
function initTicketChart(data = null) {
    const ctx = document.getElementById('ticketChart');
    if (!ctx) return;
    
    if (ticketChart) {
        ticketChart.destroy();
    }
    
    const defaultData = {
        labels: ['指令记录', '逐项令', '综合令', '许可令'],
        values: [45, 34, 0, 0]
    };
    
    const chartData = data || defaultData;
    
    ticketChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: chartData.labels,
            datasets: [{
                data: chartData.values,
                backgroundColor: [
                    chartColors.primary,
                    chartColors.yellow,
                    chartColors.gray,
                    chartColors.purple
                ],
                borderColor: '#0a1628',
                borderWidth: 2,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipText,
                    bodyColor: chartColors.tooltipText,
                    borderColor: chartColors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 6,
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 初始化网络发令情况图表（环形图）
 */
function initNetworkOrderChart(data = null) {
    const ctx = document.getElementById('networkOrderChart');
    if (!ctx) return;
    
    if (networkOrderChart) {
        networkOrderChart.destroy();
    }
    
    // 空数据（无模拟数据）
    const defaultData = {
        labels: ['逐项令', '许可令'],
        values: [0, 0]
    };
    
    const chartData = data || defaultData;
    
    networkOrderChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: chartData.labels,
            datasets: [{
                data: chartData.values,
                backgroundColor: [
                    chartColors.yellow,
                    chartColors.gray
                ],
                borderColor: '#0a1628',
                borderWidth: 2,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipText,
                    bodyColor: chartColors.tooltipText,
                    borderColor: chartColors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 6,
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 初始化工作量时间轴图表（完整24小时）
 */
function initWorkloadTimelineChart(data = null) {
    const ctx = document.getElementById('workloadTimelineChart');
    if (!ctx) return;
    
    if (workloadTimelineChart) {
        workloadTimelineChart.destroy();
    }
    
    // 生成时间标签 (0:00-23:00 完整24小时)
    const timeLabels = [];
    for (let i = 0; i <= 23; i++) {
        timeLabels.push(`${i}:00`);
    }
    
    // 空数据（无模拟数据）
    const defaultData = {
        labels: timeLabels,
        workloadTotal: Array(24).fill(0),
        staffCapacity: Array(24).fill(0),
        plannedTask: Array(24).fill(0),
        unplannedTask: Array(24).fill(0)
    };
    
    const chartData = data || defaultData;
    
    workloadTimelineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: '工作任务总当量',
                    data: chartData.workloadTotal,
                    borderColor: chartColors.cyan,
                    backgroundColor: 'rgba(34, 211, 238, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    pointBackgroundColor: chartColors.cyan
                },
                {
                    label: '班组人员工作当量',
                    data: chartData.staffCapacity,
                    borderColor: chartColors.yellow,
                    backgroundColor: 'transparent',
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                    fill: false,
                    tension: 0,
                    pointRadius: 0
                },
                {
                    label: '计划任务当量',
                    data: chartData.plannedTask,
                    borderColor: chartColors.green,
                    backgroundColor: 'transparent',
                    borderWidth: 1.5,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 2,
                    pointBackgroundColor: chartColors.green
                },
                {
                    label: '非计划任务当量',
                    data: chartData.unplannedTask,
                    borderColor: chartColors.orange,
                    backgroundColor: 'transparent',
                    borderWidth: 1.5,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 2,
                    pointBackgroundColor: chartColors.orange
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipText,
                    bodyColor: chartColors.tooltipText,
                    borderColor: chartColors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 4,
                    padding: 10,
                    displayColors: true,
                    callbacks: {
                        title: function(items) {
                            const idx = items[0].dataIndex;
                            const total = chartData.workloadTotal[idx];
                            const isOverload = total > 5.2 * 1.5;
                            return `${items[0].label}${isOverload ? ' ⚠️' : ''}`;
                        },
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: chartColors.gridColor, drawBorder: false },
                    ticks: { 
                        color: '#5a7a9e', 
                        font: { size: 9 }, 
                        maxRotation: 0,
                        // 每2小时显示一个标签
                        callback: function(value, index) {
                            return index % 2 === 0 ? this.getLabelForValue(value) : '';
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 8,
                    grid: { color: chartColors.gridColor, drawBorder: false },
                    ticks: { color: '#5a7a9e', font: { size: 9 }, stepSize: 2 }
                }
            }
        }
    });
}

/**
 * 初始化所有图表
 */
function initAllCharts() {
    initModuleBusinessChart();
    initTicketChart();
    initNetworkOrderChart();
    initWorkloadTimelineChart();
}

/**
 * 更新工作量数据（处理真实数据）
 */
function updateWorkloadData(data) {
    // 处理工作量时间轴数据（从后端API返回的格式）
    if (data && data.hourly_details && Array.isArray(data.hourly_details)) {
        const hourlyData = data.hourly_details;
        
        // 生成时间标签
        const timeLabels = hourlyData.map((h, i) => `${i}:00`);
        
        // 提取数据
        const workloadTotal = hourlyData.map(h => h.total_equivalent || 0);
        const staffCapacity = hourlyData.map(h => h.staff_capacity || 0);
        const plannedTask = hourlyData.map(h => h.plan_equivalent || 0);
        const unplannedTask = hourlyData.map(h => h.non_plan_equivalent || 0);
        
        // 更新图表
        initWorkloadTimelineChart({
            labels: timeLabels,
            workloadTotal: workloadTotal,
            staffCapacity: staffCapacity,
            plannedTask: plannedTask,
            unplannedTask: unplannedTask
        });
        
        // 更新统计卡片
        if (data.summary) {
            const summary = data.summary;
            
            // 更新检修业务单总量（使用计划任务数）
            document.getElementById('stat-maintenance').innerHTML = 
                `${summary.total_plan_count || 0}<span class="unit">单</span>`;
            
            // 更新周计划开展量
            document.getElementById('stat-weekly-plan').innerHTML = 
                `${summary.total_plan_count || 0}<span class="unit">单</span>`;
            
            // 更新跳闸总量（使用非计划任务数）
            document.getElementById('stat-trip').innerHTML = 
                `${summary.total_non_plan_count || 0}<span class="unit">起</span>`;
            
            // 更新方式单业务总量
            document.getElementById('stat-mode-order').innerHTML = 
                `${summary.total_plan_count || 0}<span class="unit">单</span>`;
            
            // 更新当值人员信息
            const totalStaff = hourlyData.reduce((sum, h) => sum + (h.staff_count || 0), 0) / 24 || 0;
            document.getElementById('currentStaff').textContent = Math.round(totalStaff) + '人';
            
            // 更新人员当量
            const avgCapacity = hourlyData.reduce((sum, h) => sum + (h.staff_capacity || 0), 0) / 24 || 0;
            document.getElementById('staffCapacity').textContent = avgCapacity.toFixed(1);
            
            // 更新超负荷状态
            const overloadCount = summary.overload_count || 0;
            const overloadEl = document.getElementById('overloadStatus');
            if (overloadEl) {
                overloadEl.textContent = overloadCount > 0 ? '是' : '否';
                overloadEl.className = 'staff-value ' + (overloadCount > 0 ? 'warning' : 'success');
            }
            
            // 更新系统状态
            const statusText = document.querySelector('.status-text');
            if (statusText && statusText.id === 'lastUpdate') {
                statusText.textContent = new Date().toLocaleTimeString('zh-CN', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                });
            }
        }
        
        // 更新各模块业务情况图表
        const planCount = data.summary?.total_plan_count || 0;
        const nonPlanCount = data.summary?.total_non_plan_count || 0;
        initModuleBusinessChart({
            labels: ['周计划', '设备投退', '跳闸', '缺陷', '重过载', '保供电', '检修业务', '方式单'],
            values: [planCount, 0, nonPlanCount, nonPlanCount, 0, 0, planCount, planCount]
        });
        
        return;
    }
    
    // 处理其他格式的数据（旧格式兼容）
    // 更新统计卡片
    if (data.stats) {
        const stats = data.stats;
        
        // 更新检修业务单总量
        if (stats.maintenance !== undefined) {
            document.getElementById('stat-maintenance').innerHTML = 
                `${stats.maintenance}<span class="unit">单</span>`;
            document.getElementById('stat-maintenance-ongoing').textContent = stats.maintenanceOngoing || 0;
            document.getElementById('stat-maintenance-done').textContent = stats.maintenanceDone || 0;
        }
        
        // 更新周计划开展量
        if (stats.weeklyPlan !== undefined) {
            document.getElementById('stat-weekly-plan').innerHTML = 
                `${stats.weeklyPlan}<span class="unit">单</span>`;
            document.getElementById('stat-weekly-ongoing').textContent = stats.weeklyOngoing || 0;
            document.getElementById('stat-weekly-done').textContent = stats.weeklyDone || 0;
        }
        
        // 更新跳闸总量
        if (stats.trip !== undefined) {
            document.getElementById('stat-trip').innerHTML = 
                `${stats.trip}<span class="unit">起</span>`;
            document.getElementById('stat-trip-success').textContent = stats.tripSuccess || 0;
            document.getElementById('stat-trip-fail').textContent = stats.tripFail || 0;
        }
    }
    
    // 更新图表
    if (data.moduleBusiness) {
        initModuleBusinessChart(data.moduleBusiness);
    }
    if (data.ticket) {
        initTicketChart(data.ticket);
    }
    if (data.networkOrder) {
        initNetworkOrderChart(data.networkOrder);
    }
    if (data.workloadTimeline && !Array.isArray(data.workloadTimeline)) {
        initWorkloadTimelineChart(data.workloadTimeline);
    }
}

/**
 * 创建人员配置图表（用于消息内容）
 */
function createStaffingChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const canvas = document.createElement('canvas');
    canvas.style.width = '100%';
    canvas.style.height = '150px';
    container.innerHTML = '';
    container.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: '建议人数',
                data: data.values,
                backgroundColor: [
                    'rgba(59, 130, 246, 0.6)',
                    'rgba(6, 182, 212, 0.6)',
                    'rgba(34, 211, 238, 0.6)',
                    'rgba(139, 92, 246, 0.6)',
                    'rgba(236, 72, 153, 0.6)'
                ],
                borderColor: [
                    chartColors.primary,
                    chartColors.secondary,
                    chartColors.cyan,
                    chartColors.purple,
                    chartColors.pink
                ],
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipText,
                    bodyColor: chartColors.tooltipText,
                    borderColor: chartColors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 6,
                    padding: 10
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#5a7a9e', font: { size: 10 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: chartColors.gridColor, drawBorder: false },
                    ticks: { color: '#5a7a9e', font: { size: 10 }, stepSize: 5 }
                }
            }
        }
    });
}

/**
 * 创建风险等级仪表盘
 */
function createRiskGauge(containerId, value) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const canvas = document.createElement('canvas');
    canvas.style.width = '100%';
    canvas.style.height = '120px';
    container.innerHTML = '';
    container.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    // 根据值选择颜色
    let color = chartColors.green;
    if (value > 70) {
        color = chartColors.red;
    } else if (value > 40) {
        color = chartColors.orange;
    }
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [value, 100 - value],
                backgroundColor: [color, 'rgba(100, 116, 139, 0.2)'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        },
        plugins: [{
            id: 'centerText',
            beforeDraw: function(chart) {
                const width = chart.width;
                const height = chart.height;
                const ctx = chart.ctx;
                
                ctx.restore();
                const fontSize = (height / 80).toFixed(2);
                ctx.font = `bold ${fontSize}em sans-serif`;
                ctx.textBaseline = 'middle';
                ctx.fillStyle = color;
                
                const text = value + '%';
                const textX = Math.round((width - ctx.measureText(text).width) / 2);
                const textY = height / 2;
                
                ctx.fillText(text, textX, textY);
                ctx.save();
            }
        }]
    });
}

// 页面加载完成后初始化图表
document.addEventListener('DOMContentLoaded', function() {
    initAllCharts();
});
