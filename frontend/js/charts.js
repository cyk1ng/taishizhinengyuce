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
 * 初始化各模块业务情况图表（折线图）
 */
function initModuleBusinessChart(data = null) {
    const ctx = document.getElementById('moduleBusinessChart');
    if (!ctx) return;
    
    if (moduleBusinessChart) {
        moduleBusinessChart.destroy();
    }
    
    const defaultData = {
        labels: ['周计划', '设备投退', '跳闸', '缺陷', '重过载', '保供电', '检修业务', '方式单'],
        values: [25, 0, 11, 8, 0, 3, 15, 20]
    };
    
    const chartData = data || defaultData;
    
    moduleBusinessChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: '业务数量',
                data: chartData.values,
                borderColor: chartColors.cyan,
                backgroundColor: 'rgba(34, 211, 238, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointBackgroundColor: chartColors.cyan,
                pointBorderColor: '#0a1628',
                pointBorderWidth: 2,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: chartColors.primary
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
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
                        title: function(items) {
                            return items[0].label;
                        },
                        label: function(context) {
                            const value = context.parsed.y;
                            return `${context.label}: ${value}单 (${value}起)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: chartColors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#5a7a9e',
                        font: { size: 10 },
                        maxRotation: 0
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 30,
                    grid: {
                        color: chartColors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#5a7a9e',
                        font: { size: 10 },
                        stepSize: 10
                    }
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
    
    const defaultData = {
        labels: ['逐项令', '许可令'],
        values: [106, 0]
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
 * 初始化工作量时间轴图表
 */
function initWorkloadTimelineChart(data = null) {
    const ctx = document.getElementById('workloadTimelineChart');
    if (!ctx) return;
    
    if (workloadTimelineChart) {
        workloadTimelineChart.destroy();
    }
    
    // 生成时间标签 (8:00-21:00)
    const timeLabels = [];
    for (let i = 8; i <= 20; i++) {
        timeLabels.push(`${i}:00-${i+1}:00`);
    }
    
    const defaultData = {
        labels: timeLabels,
        workloadTotal: [0, 2.5, 3.8, 4.2, 3.5, 2.8, 3.2, 4.5, 5.2, 4.8, 3.5, 2.8, 0],
        staffCapacity: [5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2],
        plannedTask: [0, 1.5, 2.0, 2.5, 1.8, 1.2, 1.5, 2.5, 3.0, 2.8, 2.0, 1.5, 0],
        unplannedTask: [0, 1.0, 1.8, 1.7, 1.7, 1.6, 1.7, 2.0, 2.2, 2.0, 1.5, 1.3, 0]
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
                    backgroundColor: 'rgba(34, 211, 238, 0.05)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 3,
                    pointBackgroundColor: chartColors.cyan,
                    pointBorderColor: '#0a1628',
                    pointBorderWidth: 1
                },
                {
                    label: '班组人员工作当量',
                    data: chartData.staffCapacity,
                    borderColor: chartColors.yellow,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0,
                    pointRadius: 0
                },
                {
                    label: '计划任务当量',
                    data: chartData.plannedTask,
                    borderColor: chartColors.green,
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 2,
                    pointBackgroundColor: chartColors.green
                },
                {
                    label: '非计划任务当量',
                    data: chartData.unplannedTask,
                    borderColor: chartColors.orange,
                    backgroundColor: 'rgba(249, 115, 22, 0.05)',
                    borderWidth: 2,
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
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        title: function(items) {
                            const time = items[0].label;
                            const idx = items[0].dataIndex;
                            // 添加额外信息
                            const total = chartData.workloadTotal[idx];
                            const capacity = chartData.staffCapacity[idx];
                            const isOverload = total > capacity * 1.5;
                            return `${time}${isOverload ? ' ⚠️ 超负荷' : ''}`;
                        },
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y.toFixed(2);
                            return `${label}: ${value}`;
                        },
                        afterBody: function(items) {
                            const idx = items[0].dataIndex;
                            const total = chartData.workloadTotal[idx];
                            const capacity = chartData.staffCapacity[idx];
                            const currentStaff = 4;
                            const humanCapacity = 1.3;
                            
                            // 计算需增派人数
                            const neededStaff = Math.ceil((total / (humanCapacity * 1.5)) - currentStaff);
                            const needMore = neededStaff > 0 ? `需增派: ${neededStaff}人` : '人员充足';
                            
                            return [
                                '',
                                `班组人员工作量: ${total.toFixed(2)}`,
                                `是否超人员当量: ${total > capacity * 1.5 ? '是' : '否'}`,
                                needMore
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: chartColors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#5a7a9e',
                        font: { size: 10 },
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 8,
                    grid: {
                        color: chartColors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#5a7a9e',
                        font: { size: 10 },
                        stepSize: 2
                    }
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
 * 更新工作量数据
 */
function updateWorkloadData(data) {
    // 更新统计卡片
    if (data.stats) {
        const stats = data.stats;
        
        // 更新检修业务单总量
        if (stats.maintenance !== undefined) {
            document.getElementById('stat-maintenance').innerHTML = 
                `${stats.maintenance}<span style="font-size: 16px; margin-left: 4px;">单</span>`;
            document.getElementById('stat-maintenance-ongoing').textContent = stats.maintenanceOngoing || 0;
            document.getElementById('stat-maintenance-done').textContent = stats.maintenanceDone || 0;
        }
        
        // 更新周计划开展量
        if (stats.weeklyPlan !== undefined) {
            document.getElementById('stat-weekly-plan').innerHTML = 
                `${stats.weeklyPlan}<span style="font-size: 16px; margin-left: 4px;">单</span>`;
            document.getElementById('stat-weekly-ongoing').textContent = stats.weeklyOngoing || 0;
            document.getElementById('stat-weekly-done').textContent = stats.weeklyDone || 0;
        }
        
        // 更新跳闸总量
        if (stats.trip !== undefined) {
            document.getElementById('stat-trip').innerHTML = 
                `${stats.trip}<span style="font-size: 16px; margin-left: 4px;">起</span>`;
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
    if (data.workloadTimeline) {
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
