/**
 * Chart.js 配置与初始化
 * 配网调度智能预测系统 - 淡蓝色电力主题
 */

// 图表全局配置
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif';
Chart.defaults.color = '#4a6fa5';
Chart.defaults.borderColor = 'rgba(184, 212, 232, 0.3)';

// 颜色主题
const chartColors = {
    primary: '#0078d4',
    secondary: '#00b4d8',
    electric: '#00d4ff',
    success: '#00c853',
    warning: '#ff9800',
    danger: '#f44336',
    purple: '#7c4dff',
    pink: '#e91e63',
    gray: '#90a4ae',
    gridColor: 'rgba(184, 212, 232, 0.2)',
    tooltipBg: 'rgba(255, 255, 255, 0.95)',
    tooltipText: '#1a365d'
};

// 预测趋势图表
let predictionChart = null;

function initPredictionChart(data = null) {
    const ctx = document.getElementById('predictionChart');
    if (!ctx) return;
    
    // 销毁旧图表
    if (predictionChart) {
        predictionChart.destroy();
    }
    
    // 默认数据
    const defaultData = {
        labels: ['3/23', '3/24', '3/25', '3/26', '3/27', '3/28', '3/29'],
        predicted: [45, 52, 68, 55, 72, 48, 60],
        actual: [42, 50, 65, 53, null, null, null]
    };
    
    const chartData = data || defaultData;
    
    predictionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: '预测业务量',
                    data: chartData.predicted,
                    borderColor: chartColors.primary,
                    backgroundColor: 'rgba(0, 120, 212, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointBackgroundColor: chartColors.primary,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverRadius: 7,
                    pointHoverBackgroundColor: chartColors.electric,
                    pointHoverBorderColor: '#fff',
                    pointStyle: 'rectRot',
                    order: 2
                },
                {
                    label: '实际业务量',
                    data: chartData.actual,
                    borderColor: chartColors.purple,
                    backgroundColor: 'rgba(124, 77, 255, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointBackgroundColor: chartColors.purple,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverRadius: 7,
                    pointHoverBackgroundColor: chartColors.pink,
                    pointHoverBorderColor: '#fff',
                    order: 1
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
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 11,
                            weight: '500'
                        },
                        color: chartColors.tooltipText
                    }
                },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipText,
                    bodyColor: chartColors.tooltipText,
                    borderColor: chartColors.primary,
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    displayColors: true,
                    usePointStyle: true,
                    callbacks: {
                        title: function(items) {
                            return '📅 ' + items[0].label;
                        },
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            if (value === null) return null;
                            return label + ': ' + value + ' 件';
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
                        color: chartColors.tooltipText,
                        font: {
                            size: 11,
                            weight: '500'
                        },
                        padding: 8
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 80,
                    grid: {
                        color: chartColors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: chartColors.tooltipText,
                        font: {
                            size: 11
                        },
                        padding: 8,
                        stepSize: 20
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// 更新预测图表
function updatePredictionChart(data) {
    if (!predictionChart) {
        initPredictionChart(data);
        return;
    }
    
    predictionChart.data.labels = data.labels;
    predictionChart.data.datasets[0].data = data.predicted;
    predictionChart.data.datasets[1].data = data.actual || [];
    predictionChart.update('active');
}

// 人员配置图表
function createStaffingChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // 创建 Canvas
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
                    'rgba(0, 120, 212, 0.6)',
                    'rgba(0, 180, 216, 0.6)',
                    'rgba(0, 212, 255, 0.6)',
                    'rgba(124, 77, 255, 0.6)',
                    'rgba(233, 30, 99, 0.6)'
                ],
                borderColor: [
                    chartColors.primary,
                    chartColors.secondary,
                    chartColors.electric,
                    chartColors.purple,
                    chartColors.pink
                ],
                borderWidth: 2,
                borderRadius: 6,
                borderSkipped: false
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
                    borderColor: chartColors.primary,
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: chartColors.tooltipText,
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: chartColors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: chartColors.tooltipText,
                        font: {
                            size: 10
                        },
                        stepSize: 5
                    }
                }
            }
        }
    });
}

// 风险等级图表
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
    let color = chartColors.success;
    if (value > 70) {
        color = chartColors.danger;
    } else if (value > 40) {
        color = chartColors.warning;
    }
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [value, 100 - value],
                backgroundColor: [color, chartColors.gridColor],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            circumference: 180,
            rotation: -90,
            cutout: '75%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            }
        },
        plugins: [{
            id: 'centerText',
            afterDraw: function(chart) {
                const ctx = chart.ctx;
                const width = chart.width;
                const height = chart.height;
                
                ctx.restore();
                ctx.font = 'bold 24px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.fillStyle = color;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(value + '%', width / 2, height * 0.75);
                
                ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.fillStyle = chartColors.tooltipText;
                ctx.fillText('风险指数', width / 2, height * 0.9);
                
                ctx.save();
            }
        }]
    });
}

// 业务类型分布饼图
function createDistributionChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const canvas = document.createElement('canvas');
    canvas.style.width = '100%';
    canvas.style.height = '150px';
    container.innerHTML = '';
    container.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: [
                    chartColors.primary,
                    chartColors.secondary,
                    chartColors.electric,
                    chartColors.purple,
                    chartColors.pink
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        padding: 10,
                        font: {
                            size: 11
                        },
                        color: chartColors.tooltipText
                    }
                },
                tooltip: {
                    backgroundColor: chartColors.tooltipBg,
                    titleColor: chartColors.tooltipText,
                    bodyColor: chartColors.tooltipText,
                    borderColor: chartColors.primary,
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((context.raw / total) * 100);
                            return context.label + ': ' + percentage + '%';
                        }
                    }
                }
            }
        }
    });
}

// 实时数据流图表
function createRealtimeChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const canvas = document.createElement('canvas');
    canvas.style.width = '100%';
    canvas.style.height = '100px';
    container.innerHTML = '';
    container.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    const gradient = ctx.createLinearGradient(0, 0, 0, 100);
    gradient.addColorStop(0, 'rgba(0, 212, 255, 0.3)');
    gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                borderColor: chartColors.electric,
                backgroundColor: gradient,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0
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
                    enabled: false
                }
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    display: false
                }
            },
            animation: {
                duration: 0
            }
        }
    });
}

// 初始化所有图表
function initAllCharts() {
    initPredictionChart();
    
    // 可以根据需要初始化其他图表
    console.log('📊 图表初始化完成');
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 延迟初始化图表，确保 DOM 完全加载
    setTimeout(initAllCharts, 100);
});

// 导出函数
window.updatePredictionChart = updatePredictionChart;
window.createStaffingChart = createStaffingChart;
window.createRiskGauge = createRiskGauge;
window.createDistributionChart = createDistributionChart;
window.createRealtimeChart = createRealtimeChart;
