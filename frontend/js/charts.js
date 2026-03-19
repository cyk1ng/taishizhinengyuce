/**
 * ⚡ 配网调度智能预测系统 - 图表配置（炫酷版）
 */

// Chart.js 全局配置
Chart.defaults.color = '#a0aec0';
Chart.defaults.borderColor = 'rgba(0, 212, 255, 0.15)';
Chart.defaults.font.family = 'Microsoft YaHei, sans-serif';

/**
 * 图表管理类
 */
class ChartManager {
    constructor() {
        this.charts = {};
        this.initCharts();
    }

    /**
     * 初始化所有图表
     */
    initCharts() {
        this.initPredictionChart();
    }

    /**
     * 初始化预测趋势图 - 炫酷电光风格
     */
    initPredictionChart() {
        const ctx = document.getElementById('predictionChart');
        if (!ctx) return;

        // 创建渐变
        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 250);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.5)');
        gradient.addColorStop(0.5, 'rgba(0, 150, 255, 0.2)');
        gradient.addColorStop(1, 'rgba(0, 100, 200, 0)');

        this.charts.prediction = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '预测业务量',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#00d4ff',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    pointHoverBackgroundColor: '#00ffff',
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 3,
                    shadowOffsetX: 0,
                    shadowOffsetY: 0,
                    shadowBlur: 10,
                    shadowColor: 'rgba(0, 212, 255, 0.5)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#00d4ff',
                            font: {
                                size: 12,
                                weight: 'bold'
                            },
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(5, 15, 35, 0.95)',
                        titleColor: '#00d4ff',
                        bodyColor: '#e0e0e0',
                        borderColor: '#00d4ff',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        titleFont: {
                            size: 13,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 12
                        },
                        callbacks: {
                            label: function(context) {
                                return '⚡ 业务量: ' + context.parsed.y;
                            }
                        },
                        shadowOffsetX: 0,
                        shadowOffsetY: 4,
                        shadowBlur: 10,
                        shadowColor: 'rgba(0, 212, 255, 0.3)'
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(0, 212, 255, 0.08)',
                            drawBorder: false,
                            lineWidth: 1
                        },
                        ticks: {
                            color: '#9ca3af',
                            font: {
                                size: 10
                            },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 212, 255, 0.08)',
                            drawBorder: false,
                            lineWidth: 1
                        },
                        ticks: {
                            color: '#9ca3af',
                            font: {
                                size: 10
                            },
                            padding: 10
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animation: {
                    duration: 1500,
                    easing: 'easeOutQuart'
                },
                elements: {
                    line: {
                        shadowOffsetX: 0,
                        shadowOffsetY: 0,
                        shadowBlur: 10,
                        shadowColor: 'rgba(0, 212, 255, 0.5)'
                    }
                }
            }
        });
    }

    /**
     * 更新预测图表数据
     */
    updatePredictionChart(labels, data) {
        if (this.charts.prediction) {
            this.charts.prediction.data.labels = labels;
            this.charts.prediction.data.datasets[0].data = data;
            this.charts.prediction.update('active');
        }
    }

    /**
     * 创建炫酷柱状图
     */
    createBarChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: data.label || '数据',
                    data: data.values,
                    backgroundColor: [
                        'rgba(0, 212, 255, 0.8)',
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(147, 51, 234, 0.8)',
                        'rgba(34, 197, 94, 0.8)',
                        'rgba(251, 191, 36, 0.8)'
                    ],
                    borderColor: [
                        '#00d4ff',
                        '#3b82f6',
                        '#9333ea',
                        '#22c55e',
                        '#fbbf24'
                    ],
                    borderWidth: 2,
                    borderRadius: 6,
                    shadowOffsetX: 0,
                    shadowOffsetY: 4,
                    shadowBlur: 8,
                    shadowColor: 'rgba(0, 212, 255, 0.3)'
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
                        backgroundColor: 'rgba(5, 15, 35, 0.95)',
                        titleColor: '#00d4ff',
                        bodyColor: '#e0e0e0',
                        borderColor: '#00d4ff',
                        borderWidth: 1,
                        padding: 12
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 212, 255, 0.08)'
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    }
                }
            }
        });
    }

    /**
     * 创建炫酷饼图
     */
    createPieChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: [
                        'rgba(0, 212, 255, 0.8)',
                        'rgba(147, 51, 234, 0.8)',
                        'rgba(34, 197, 94, 0.8)',
                        'rgba(251, 191, 36, 0.8)',
                        'rgba(239, 68, 68, 0.8)'
                    ],
                    borderColor: '#0a0e27',
                    borderWidth: 3,
                    shadowOffsetX: 0,
                    shadowOffsetY: 4,
                    shadowBlur: 10,
                    shadowColor: 'rgba(0, 212, 255, 0.5)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#a0aec0',
                            padding: 15,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(5, 15, 35, 0.95)',
                        titleColor: '#00d4ff',
                        bodyColor: '#e0e0e0',
                        borderColor: '#00d4ff',
                        borderWidth: 1
                    }
                },
                cutout: '60%'
            }
        });
    }

    /**
     * 清空所有图表
     */
    clearAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        });
        this.charts = {};
        this.initCharts();
    }
}

// 创建全局图表管理器实例
const chartManager = new ChartManager();

// 导出
window.ChartManager = ChartManager;
window.chartManager = chartManager;
