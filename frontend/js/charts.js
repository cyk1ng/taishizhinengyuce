/**
 * ⚡ 配网调度智能预测系统 - 图表配置
 */

// Chart.js 全局配置 - 电力系统主题
Chart.defaults.color = '#a0aec0';
Chart.defaults.borderColor = 'rgba(0, 212, 255, 0.2)';
Chart.defaults.font.family = 'Consolas, Monaco, monospace';

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
     * 初始化预测趋势图 - 电光风格
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
                    borderColor: 'rgb(0, 212, 255)',
                    backgroundColor: (context) => {
                        const ctx = context.chart.ctx;
                        const gradient = ctx.createLinearGradient(0, 0, 0, 200);
                        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.3)');
                        gradient.addColorStop(1, 'rgba(0, 212, 255, 0.0)');
                        return gradient;
                    },
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#00d4ff',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#00e5ff',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 3
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
                                size: 11,
                                family: 'Consolas'
                            },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(10, 14, 39, 0.95)',
                        titleColor: '#00d4ff',
                        bodyColor: '#e0e0e0',
                        borderColor: 'rgba(0, 212, 255, 0.5)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        titleFont: {
                            family: 'Consolas',
                            size: 12
                        },
                        bodyFont: {
                            family: 'Consolas',
                            size: 11
                        },
                        callbacks: {
                            label: function(context) {
                                return `⚡ 业务量: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(0, 212, 255, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#a0aec0',
                            font: {
                                size: 10,
                                family: 'Consolas'
                            },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 212, 255, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#a0aec0',
                            font: {
                                size: 10,
                                family: 'Consolas'
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
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
     * 创建业务量对比柱状图 - 电光风格
     */
    createComparisonChart(canvasId, data) {
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
                    label: '预测值',
                    data: data.predicted,
                    backgroundColor: 'rgba(0, 212, 255, 0.6)',
                    borderColor: 'rgb(0, 212, 255)',
                    borderWidth: 1,
                    borderRadius: 4
                }, {
                    label: '实际值',
                    data: data.actual,
                    backgroundColor: 'rgba(168, 85, 247, 0.6)',
                    borderColor: 'rgb(168, 85, 247)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#a0aec0',
                            font: {
                                family: 'Consolas'
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(0, 212, 255, 0.1)'
                        },
                        ticks: {
                            color: '#a0aec0'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 212, 255, 0.1)'
                        },
                        ticks: {
                            color: '#a0aec0'
                        }
                    }
                }
            }
        });
    }

    /**
     * 创建人员配置饼图 - 电光风格
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
                        'rgba(0, 212, 255, 0.8)',
                        'rgba(168, 85, 247, 0.8)',
                        'rgba(34, 197, 94, 0.8)',
                        'rgba(251, 191, 36, 0.8)',
                        'rgba(239, 68, 68, 0.8)'
                    ],
                    borderWidth: 2,
                    borderColor: '#0a0e27'
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
                            padding: 10,
                            font: {
                                family: 'Consolas',
                                size: 10
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * 创建风险等级雷达图 - 电光风格
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
                            color: '#a0aec0',
                            backdropColor: 'transparent',
                            font: {
                                size: 9
                            }
                        },
                        grid: {
                            color: 'rgba(0, 212, 255, 0.2)'
                        },
                        angleLines: {
                            color: 'rgba(0, 212, 255, 0.2)'
                        },
                        pointLabels: {
                            color: '#a0aec0',
                            font: {
                                size: 10,
                                family: 'Consolas'
                            }
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
