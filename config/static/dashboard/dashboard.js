// Dashboard Charts Initialization
document.addEventListener('DOMContentLoaded', function() {
    // Operations Activity Chart
    const operationsCtx = document.getElementById('operationsActivityChart');
    if (operationsCtx) {
        let operationsChart;
        let currentPeriod = 'week'; // Default period

        function loadOperationsChart(period) {
            currentPeriod = period;
            fetch(`/estokada/api/operations-activity/?period=${period}`)
                .then(response => response.json())
                .then(data => {
                    if (operationsChart) {
                        operationsChart.destroy();
                    }
                    
                    // Set colors for different operation types
                    const colors = {
                        'in': 'rgba(40, 167, 69, 0.7)',       // Green for Receive
                        'out': 'rgba(0, 123, 255, 0.7)',      // Blue for Shipment
                        'transfer': 'rgba(23, 162, 184, 0.7)', // Cyan for Transfer
                        'production': 'rgba(255, 193, 7, 0.7)' // Yellow for Production
                    };

                    // Prepare datasets
                    const datasets = Object.keys(data.operations).map(type => {
                        return {
                            label: data.labels[type],
                            data: data.operations[type],
                            backgroundColor: colors[type],
                            borderColor: colors[type].replace('0.7', '1'),
                            borderWidth: 1,
                            borderRadius: 4,
                            barPercentage: 0.6,
                            categoryPercentage: 0.8
                        };
                    });

                    // Create chart
                    operationsChart = new Chart(operationsCtx, {
                        type: 'bar',
                        data: {
                            labels: data.dates,
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'top',
                                    labels: {
                                        usePointStyle: true,
                                        padding: 15
                                    }
                                },
                                tooltip: {
                                    mode: 'index',
                                    intersect: false,
                                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                                    titleColor: '#495057',
                                    bodyColor: '#495057',
                                    borderColor: '#e9ecef',
                                    borderWidth: 1,
                                    padding: 12,
                                    boxPadding: 6,
                                    usePointStyle: true,
                                    callbacks: {
                                        label: function(context) {
                                            return `${context.dataset.label}: ${context.raw} операций`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    grid: {
                                        display: false
                                    }
                                },
                                y: {
                                    beginAtZero: true,
                                    grid: {
                                        borderDash: [2, 4],
                                        color: '#e9ecef'
                                    },
                                    ticks: {
                                        precision: 0
                                    }
                                }
                            },
                            animation: {
                                duration: 1000,
                                easing: 'easeOutQuart'
                            }
                        }
                    });
                })
                .catch(error => console.error('Error loading operations chart:', error));
        }

        // Initialize chart with default period
        loadOperationsChart(currentPeriod);

        // Add event listeners for period selection
        document.getElementById('periodWeek').addEventListener('click', function() {
            document.getElementById('periodWeek').classList.add('active');
            document.getElementById('periodMonth').classList.remove('active');
            loadOperationsChart('week');
        });

        document.getElementById('periodMonth').addEventListener('click', function() {
            document.getElementById('periodMonth').classList.add('active');
            document.getElementById('periodWeek').classList.remove('active');
            loadOperationsChart('month');
        });
    }

    // Top Products Chart
    const topProductsCtx = document.getElementById('topProductsChart');
    if (topProductsCtx) {
        fetch('/estokada/api/top-products/')
            .then(response => response.json())
            .then(data => {
                // Generate colors for each product
                const generateGradient = (ctx, index) => {
                    const colors = [
                        ['#3B82F6', '#93C5FD'], // Blue
                        ['#10B981', '#6EE7B7'], // Green
                        ['#F59E0B', '#FCD34D'], // Yellow
                        ['#EF4444', '#FCA5A5'], // Red
                        ['#8B5CF6', '#C4B5FD']  // Purple
                    ];
                    
                    const colorPair = colors[index % colors.length];
                    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                    gradient.addColorStop(0, colorPair[0]);
                    gradient.addColorStop(1, colorPair[1]);
                    return gradient;
                };

                // Create chart
                const topProductsChart = new Chart(topProductsCtx, {
                    type: 'doughnut',
                    data: {
                        labels: data.products.map(p => p.name),
                        datasets: [{
                            data: data.products.map(p => p.volume),
                            backgroundColor: function(context) {
                                const chart = context.chart;
                                const {ctx, chartArea} = chart;
                                if (!chartArea) {
                                    return null;
                                }
                                return generateGradient(ctx, context.dataIndex);
                            },
                            borderWidth: 1,
                            borderColor: '#fff',
                            hoverBorderWidth: 2,
                            hoverOffset: 10
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '75%',
                        plugins: {
                            legend: {
                                position: 'right',
                                labels: {
                                    usePointStyle: true,
                                    padding: 15,
                                    generateLabels: function(chart) {
                                        const original = Chart.overrides.doughnut.plugins.legend.labels.generateLabels;
                                        const labels = original.call(this, chart);
                                        
                                        labels.forEach((label, i) => {
                                            label.text = `${label.text} (${data.products[i].percentage}%)`;
                                        });
                                        
                                        return labels;
                                    }
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                                titleColor: '#495057',
                                bodyColor: '#495057',
                                borderColor: '#e9ecef',
                                borderWidth: 1,
                                padding: 12,
                                callbacks: {
                                    label: function(context) {
                                        const value = context.raw;
                                        const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${context.label}: ${value} т (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: {
                            animateScale: true,
                            animateRotate: true,
                            duration: 1200,
                            easing: 'easeOutCirc'
                        }
                    }
                });

                // Add inner text with total volume
                Chart.register({
                    id: 'doughnutInnerText',
                    beforeDraw: function(chart) {
                        const totalVolume = data.products.reduce((sum, product) => sum + product.volume, 0);
                        
                        const {ctx, chartArea: {top, bottom, left, right, width, height}} = chart;
                        ctx.save();
                        
                        // Draw total volume
                        ctx.fillStyle = '#343a40';
                        ctx.font = 'bold 16px Arial';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillText(`${totalVolume.toFixed(1)} т`, width / 2 + left, height / 2 + top - 10);
                        
                        // Draw label
                        ctx.fillStyle = '#6c757d';
                        ctx.font = '12px Arial';
                        ctx.fillText('Всего объем', width / 2 + left, height / 2 + top + 15);
                        
                        ctx.restore();
                    }
                });
            })
            .catch(error => console.error('Error loading top products chart:', error));
    }
}); 