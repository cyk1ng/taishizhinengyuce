/**
 * 配网调度业务量智能预测系统 - 图表配置
 */

// Chart.js 全局配置
Chart.defaults.color = '#9ca3af';
Chart.defaults.borderColor = '#374151';
Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';

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
     * 初始化预测趋势图
     */
    initPredictionChart() {
        const ctx = document.getElementById('predictionChart');
        if (!ctx) return;

        this.charts.prediction = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '预测业务量',
                    data: [],
                    borderColor: 'rgb(96, 165, 250)',
                    backgroundColor: 'rgba(96, 165, 250, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgb(96, 165, 250)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
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
                            color: '#e5e7eb',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(17, 24, 39, 0.9)',
                        titleColor: '#60a5fa',
                        bodyColor: '#e5e7eb',
                        borderColor: '#374151',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return `业务量: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(55, 65, 81, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#9ca3af',
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(55, 65, 81, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    /**
     * 更新预测图表数据
     * @param {Array} labels - X轴标签
     * @param {Array} data - 数据点
     */
    updatePredictionChart(labels, data) {
        if (this.charts.prediction) {
            this.charts.prediction.data.labels = labels;
            this.charts.prediction.data.datasets[0].data = data;
            this.charts.prediction.update('active');
        }
    }

    /**
     * 创建业务量对比柱状图
     * @param {string} canvasId - Canvas ID
     * @param {object} data - 图表数据
     */
    createComparisonChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        // 如果已存在图表，先销毁
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: '预测值',
                    data: data.predicted,
                    backgroundColor: 'rgba(96, 165, 250, 0.8)',
                    borderColor: 'rgb(96, 165, 250)',
                    borderWidth: 1
                }, {
                    label: '实际值',
                    data: data.actual,
                    backgroundColor: 'rgba(167, 139, 250, 0.8)',
                    borderColor: 'rgb(167, 139, 250)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(55, 65, 81, 0.5)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(55, 65, 81, 0.5)'
                        }
                    }
                }
            }
        });
    }

    /**
     * 创建人员配置饼图
     * @param {string} canvasId - Canvas ID
     * @param {object} data - 图表数据
     */
    createStaffingPieChart(canvasId, data) {
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
                        'rgba(96, 165, 250, 0.8)',
                        'rgba(167, 139, 250, 0.8)',
                        'rgba(52, 211, 153, 0.8)',
                        'rgba(251, 191, 36, 0.8)',
                        'rgba(239, 68, 68, 0.8)'
                    ],
                    borderWidth: 2,
                    borderColor: '#1f2937'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#e5e7eb',
                            padding: 10
                        }
                    }
                }
            }
        });
    }

    /**
     * 创建风险等级雷达图
     * @param {string} canvasId - Canvas ID
     * @param {object} data - 图表数据
     */
    createRiskRadarChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: '风险评分',
                    data: data.values,
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    borderColor: 'rgb(239, 68, 68)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgb(239, 68, 68)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(239, 68, 68)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            color: '#9ca3af',
                            backdropColor: 'transparent'
                        },
                        grid: {
                            color: 'rgba(55, 65, 81, 0.5)'
                        },
                        angleLines: {
                            color: 'rgba(55, 65, 81, 0.5)'
                        },
                        pointLabels: {
                            color: '#e5e7eb'
                        }
                    }
                }
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
