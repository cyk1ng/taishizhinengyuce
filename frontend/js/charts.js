/**
 * 配网调度业务量智能预测系统 - 图表配置
 */

// Chart.js 全局配置 - 科技感风格
Chart.defaults.color = '#8b949e';
Chart.defaults.borderColor = '#30363d';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif';

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

        // 生成示例数据
        const labels = [];
        const data = [];
        const today = new Date();
        
        for (let i = 0; i < 7; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() + i);
            labels.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
            data.push(Math.floor(Math.random() * 30) + 40);
        }

        this.charts.prediction = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '预测业务量',
                    data: data,
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#58a6ff',
                    pointBorderColor: '#0d1117',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#00d4ff',
                    pointHoverBorderColor: '#0d1117',
                    pointHoverBorderWidth: 2
                }, {
                    label: '实际业务量',
                    data: data.map(d => d + Math.floor(Math.random() * 10) - 5),
                    borderColor: '#a371f7',
                    backgroundColor: 'rgba(163, 113, 247, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#a371f7',
                    pointBorderColor: '#0d1117',
                    pointBorderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    borderDash: [5, 5]
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
                        display: true,
                        position: 'top',
                        align: 'end',
                        labels: {
                            color: '#8b949e',
                            font: {
                                size: 11
                            },
                            boxWidth: 12,
                            boxHeight: 12,
                            borderRadius: 2,
                            useBorderRadius: true,
                            padding: 12
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 27, 34, 0.95)',
                        titleColor: '#e6edf3',
                        bodyColor: '#8b949e',
                        borderColor: '#30363d',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 6,
                        displayColors: true,
                        boxPadding: 4,
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                return ` ${label}: ${value} 次`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(48, 54, 61, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#8b949e',
                            font: {
                                size: 10
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(48, 54, 61, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#8b949e',
                            font: {
                                size: 10
                            },
                            stepSize: 20
                        }
                    }
                }
            }
        });
    }

    /**
     * 更新预测图表数据
     */
    updatePredictionChart(data) {
        if (!this.charts.prediction || !data) return;

        const labels = data.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
        });

        const values = data.map(d => d.dispatch_count);

        this.charts.prediction.data.labels = labels;
        this.charts.prediction.data.datasets[0].data = values;
        this.charts.prediction.update('none');
    }

    /**
     * 销毁所有图表
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }
}

// 初始化图表管理器
let chartManager;

document.addEventListener('DOMContentLoaded', function() {
    chartManager = new ChartManager();
});
