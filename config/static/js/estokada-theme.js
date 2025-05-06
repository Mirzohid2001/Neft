/**
 * Estokada интерактивные функции и поддержка темной темы
 */
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация темной темы
    initThemeToggle();
    
    // Поиск в таблицах
    initTableSearch();
    
    // Анимация строк таблиц
    animateTableRows();
    
    // Инициализация графиков, если они есть на странице
    if (document.getElementById('operationsChart')) {
        initCharts();
    }
});

/**
 * Инициализация переключателя темы
 */
function initThemeToggle() {
    // Проверяем, есть ли переключатель в DOM
    let themeToggle = document.getElementById('themeToggle');
    
    // Если нет, создаем его
    if (!themeToggle) {
        themeToggle = document.createElement('div');
        themeToggle.id = 'themeToggle';
        themeToggle.className = 'theme-toggle';
        
        const themeIcon = document.createElement('i');
        themeIcon.id = 'themeIcon';
        themeIcon.className = 'fas fa-moon';
        
        themeToggle.appendChild(themeIcon);
        document.body.appendChild(themeToggle);
    }
    
    const themeIcon = document.getElementById('themeIcon');
    const htmlElement = document.documentElement;
    
    // Проверка сохраненной темы
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        htmlElement.classList.add('dark-mode');
        themeIcon.classList.remove('fa-moon');
        themeIcon.classList.add('fa-sun');
    }
    
    // Переключение темы
    themeToggle.addEventListener('click', function() {
        if (htmlElement.classList.contains('dark-mode')) {
            htmlElement.classList.remove('dark-mode');
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
            localStorage.setItem('theme', 'light');
            if (typeof updateChartColors === 'function') {
                updateChartColors(false);
            }
        } else {
            htmlElement.classList.add('dark-mode');
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
            localStorage.setItem('theme', 'dark');
            if (typeof updateChartColors === 'function') {
                updateChartColors(true);
            }
        }
    });
    
    // Автоматическое определение системной темы
    if (!localStorage.getItem('theme')) {
        const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDarkMode) {
            htmlElement.classList.add('dark-mode');
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
            localStorage.setItem('theme', 'dark');
            if (typeof updateChartColors === 'function') {
                updateChartColors(true);
            }
        }
    }
}

/**
 * Инициализация поиска в таблицах
 */
function initTableSearch() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach((table, index) => {
        // Получаем контейнер таблицы
        const tableContainer = table.closest('.card');
        if (!tableContainer) return;
        
        // Получаем заголовок таблицы
        const tableHeader = tableContainer.querySelector('.card-header');
        if (!tableHeader) return;
        
        // Проверяем, есть ли уже поисковое поле
        if (tableHeader.querySelector('.search-input')) return;
        
        // Создаем ID для таблицы, если его нет
        if (!table.id) {
            table.id = `dataTable-${index}`;
        }
        
        // Создаем поисковое поле
        const searchContainer = document.createElement('div');
        searchContainer.className = 'input-group search-container';
        searchContainer.style.width = '250px';
        
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'form-control search-input';
        searchInput.placeholder = 'Поиск...';
        searchInput.dataset.target = table.id;
        
        const searchButton = document.createElement('button');
        searchButton.className = 'btn btn-light';
        searchButton.type = 'button';
        searchButton.innerHTML = '<i class="fas fa-search"></i>';
        
        searchContainer.appendChild(searchInput);
        searchContainer.appendChild(searchButton);
        
        // Если в заголовке уже есть другие элементы, добавляем d-flex
        if (tableHeader.children.length > 1) {
            tableHeader.classList.add('d-flex', 'justify-content-between', 'align-items-center');
            
            // Создаем контейнер для элементов справа
            const rightContainer = document.createElement('div');
            rightContainer.className = 'd-flex align-items-center';
            
            // Перемещаем существующие элементы
            const existingButtons = tableHeader.querySelectorAll('a.btn, button.btn');
            existingButtons.forEach(button => {
                rightContainer.appendChild(button.cloneNode(true));
                button.remove();
            });
            
            // Добавляем поисковое поле
            rightContainer.insertBefore(searchContainer, rightContainer.firstChild);
            tableHeader.appendChild(rightContainer);
        } else {
            // Если нет других элементов, добавляем поисковое поле прямо в заголовок
            tableHeader.classList.add('d-flex', 'justify-content-between', 'align-items-center');
            tableHeader.appendChild(searchContainer);
        }
        
        // Обработчик для поиска
        searchInput.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const targetTable = document.getElementById(this.dataset.target);
            if (!targetTable) return;
            
            const rows = targetTable.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const rowText = row.textContent.toLowerCase();
                if (rowText.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });
}

/**
 * Анимация строк таблицы при загрузке
 */
function animateTableRows() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach((row, index) => {
            row.style.opacity = '0';
            setTimeout(() => {
                row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                row.style.opacity = '1';
            }, 50 * index);
        });
    });
}

/**
 * Конвертация HEX в RGBA
 */
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Инициализация графиков (если включен Chart.js)
 */
function initCharts() {
    if (!window.Chart) {
        console.warn('Chart.js не загружен. Графики не будут инициализированы.');
        return;
    }
    
    // Определение основных цветов для графиков
    const chartColors = {
        light: {
            primary: '#4e73df',
            success: '#1cc88a',
            info: '#36b9cc',
            warning: '#f6c23e',
            textColor: '#5a5c69',
            gridColor: '#eaecf4'
        },
        dark: {
            primary: '#375cdb',
            success: '#17a673',
            info: '#2fafca',
            warning: '#e9b949',
            textColor: '#dfe0e4',
            gridColor: '#444a54'
        }
    };
    
    // Выбор текущих цветов в зависимости от темы
    const isDarkMode = document.documentElement.classList.contains('dark-mode');
    let currentTheme = isDarkMode ? 'dark' : 'light';
    let colors = chartColors[currentTheme];
    
    // График операций по дням - загрузка данных через API
    const operationsCtx = document.getElementById('operationsChart').getContext('2d');
    
    // Инициализация графика с пустыми данными
    window.operationsChart = new Chart(operationsCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Приемка',
                    data: [],
                    borderColor: colors.primary,
                    backgroundColor: hexToRgba(colors.primary, 0.1),
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Отгрузка',
                    data: [],
                    borderColor: colors.success,
                    backgroundColor: hexToRgba(colors.success, 0.1),
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Перемещение',
                    data: [],
                    borderColor: colors.info,
                    backgroundColor: hexToRgba(colors.info, 0.1),
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Производство',
                    data: [],
                    borderColor: colors.warning,
                    backgroundColor: hexToRgba(colors.warning, 0.1),
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: colors.textColor
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        color: colors.gridColor
                    },
                    ticks: {
                        color: colors.textColor
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: colors.gridColor
                    },
                    ticks: {
                        color: colors.textColor
                    }
                }
            }
        }
    });
    
    // Функция для обновления данных графика операций
    function updateOperationsChart(period = 'week') {
        fetch(`/estokada/api/operations-chart-data/?period=${period}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Сетевая ошибка при загрузке данных графика');
                }
                return response.json();
            })
            .then(data => {
                // Обновляем данные графика
                window.operationsChart.data.labels = data.labels;
                
                // Обновляем данные для каждого набора
                for (let i = 0; i < data.datasets.length; i++) {
                    window.operationsChart.data.datasets[i].data = data.datasets[i].data;
                }
                
                // Перерисовываем график
                window.operationsChart.update();
                
                // Отправляем событие о загрузке данных
                document.dispatchEvent(new CustomEvent('chartDataLoaded', {
                    detail: {
                        chartType: 'operations',
                        period: period
                    }
                }));
            })
            .catch(error => {
                console.error('Ошибка при загрузке данных графика:', error);
            });
    }
    
    // Круговая диаграмма типов операций
    if (document.getElementById('operationTypesChart')) {
        const typesCtx = document.getElementById('operationTypesChart').getContext('2d');
        
        // Инициализация с пустыми данными
        window.typesChart = new Chart(typesCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        colors.primary,
                        colors.success,
                        colors.info,
                        colors.warning
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: colors.textColor,
                            padding: 15,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    }
                },
                cutout: '65%'
            }
        });
        
        // Функция для обновления круговой диаграммы
        function updateTypesChart(period = 'week') {
            fetch(`/estokada/api/types-chart-data/?period=${period}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Сетевая ошибка при загрузке данных диаграммы');
                    }
                    return response.json();
                })
                .then(data => {
                    // Обновляем данные диаграммы
                    window.typesChart.data.labels = data.labels;
                    window.typesChart.data.datasets[0].data = data.data;
                    
                    // Перерисовываем диаграмму
                    window.typesChart.update();
                    
                    // Отправляем событие о загрузке данных
                    document.dispatchEvent(new CustomEvent('chartDataLoaded', {
                        detail: {
                            chartType: 'types',
                            period: period
                        }
                    }));
                })
                .catch(error => {
                    console.error('Ошибка при загрузке данных диаграммы:', error);
                });
        }
    }
    
    // Первоначальная загрузка данных
    updateOperationsChart('week');
    if (window.typesChart) {
        updateTypesChart('week');
    }
    
    // Автоматическое обновление каждые 60 секунд
    const updateInterval = 60 * 1000; // 60 секунд
    setInterval(() => {
        updateOperationsChart(getCurrentPeriod());
        if (window.typesChart) {
            updateTypesChart(getCurrentPeriod());
        }
    }, updateInterval);
    
    // Функция для получения текущего выбранного периода
    function getCurrentPeriod() {
        const periodButton = document.getElementById('periodDropdown');
        if (!periodButton) return 'week';
        
        const buttonText = periodButton.textContent.trim().toLowerCase();
        
        if (buttonText.includes('месяц')) {
            return 'month';
        } else if (buttonText.includes('квартал')) {
            return 'quarter';
        } else {
            return 'week';
        }
    }
    
    // Обработка изменения периода в графике
    const periodLinks = document.querySelectorAll('.chart-period');
    const periodButton = document.getElementById('periodDropdown');
    
    if (periodLinks.length > 0 && periodButton) {
        periodLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const period = this.getAttribute('data-period');
                periodButton.textContent = this.textContent;
                
                // Запрос новых данных через API
                updateOperationsChart(period);
                if (window.typesChart) {
                    updateTypesChart(period);
                }
            });
        });
    }
}

/**
 * Обновление цветов графиков при смене темы
 */
function updateChartColors(isDark) {
    if (!window.Chart) return;
    
    const chartColors = {
        light: {
            primary: '#4e73df',
            success: '#1cc88a',
            info: '#36b9cc',
            warning: '#f6c23e',
            textColor: '#5a5c69',
            gridColor: '#eaecf4'
        },
        dark: {
            primary: '#375cdb',
            success: '#17a673',
            info: '#2fafca',
            warning: '#e9b949',
            textColor: '#dfe0e4',
            gridColor: '#444a54'
        }
    };
    
    const theme = isDark ? 'dark' : 'light';
    const colors = chartColors[theme];
    
    // Обновление линейного графика
    if (window.operationsChart) {
        window.operationsChart.data.datasets[0].borderColor = colors.primary;
        window.operationsChart.data.datasets[0].backgroundColor = hexToRgba(colors.primary, 0.1);
        window.operationsChart.data.datasets[1].borderColor = colors.success;
        window.operationsChart.data.datasets[1].backgroundColor = hexToRgba(colors.success, 0.1);
        window.operationsChart.data.datasets[2].borderColor = colors.info;
        window.operationsChart.data.datasets[2].backgroundColor = hexToRgba(colors.info, 0.1);
        
        window.operationsChart.options.plugins.legend.labels.color = colors.textColor;
        window.operationsChart.options.scales.x.grid.color = colors.gridColor;
        window.operationsChart.options.scales.x.ticks.color = colors.textColor;
        window.operationsChart.options.scales.y.grid.color = colors.gridColor;
        window.operationsChart.options.scales.y.ticks.color = colors.textColor;
        
        window.operationsChart.update();
    }
    
    // Обновление круговой диаграммы
    if (window.typesChart) {
        window.typesChart.data.datasets[0].backgroundColor = [
            colors.primary,
            colors.success,
            colors.info,
            colors.warning
        ];
        window.typesChart.options.plugins.legend.labels.color = colors.textColor;
        window.typesChart.update();
    }
} 