document.addEventListener('DOMContentLoaded', function() {
    // Function to initialize the severity chart if the element exists
    function initializeSeverityChart() {
        const severityChartElem = document.getElementById('severityChart');
        if (!severityChartElem) return;
        
        // Get the severity counts from the data attributes
        const mildCount = parseInt(severityChartElem.getAttribute('data-mild') || 0);
        const moderateCount = parseInt(severityChartElem.getAttribute('data-moderate') || 0);
        const severeCount = parseInt(severityChartElem.getAttribute('data-severe') || 0);
        const unknownCount = parseInt(severityChartElem.getAttribute('data-unknown') || 0);
        
        const ctx = severityChartElem.getContext('2d');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Mild', 'Moderate', 'Severe', 'Unknown'],
                datasets: [{
                    data: [mildCount, moderateCount, severeCount, unknownCount],
                    backgroundColor: [
                        '#28a745', // green for mild
                        '#ffc107', // yellow for moderate
                        '#dc3545', // red for severe
                        '#6c757d'  // gray for unknown
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Function to initialize patient medication history chart
    function initializeMedicationHistoryChart() {
        const medicationChartElem = document.getElementById('medicationHistoryChart');
        if (!medicationChartElem) return;
        
        // This would normally get data from the DOM or an API call
        // For demonstration, we're using placeholder data
        const medicationNames = JSON.parse(medicationChartElem.getAttribute('data-medications') || '[]');
        const startDates = JSON.parse(medicationChartElem.getAttribute('data-start-dates') || '[]');
        const endDates = JSON.parse(medicationChartElem.getAttribute('data-end-dates') || '[]');
        
        if (medicationNames.length === 0) return;
        
        // Convert dates to days ago
        const now = new Date();
        const formatDate = (dateStr) => {
            if (!dateStr) return now;
            return new Date(dateStr);
        };
        
        const datasets = medicationNames.map((name, i) => {
            const start = formatDate(startDates[i]);
            // If end date is null, use current date
            const end = endDates[i] ? formatDate(endDates[i]) : now;
            
            return {
                label: name,
                data: [{
                    x: start,
                    y: i,
                    x2: end
                }],
                backgroundColor: `hsl(${(i * 30) % 360}, 70%, 60%)`,
                borderWidth: 0,
                barPercentage: 0.6
            };
        });
        
        const ctx = medicationChartElem.getContext('2d');
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                datasets: datasets
            },
            options: {
                indexAxis: 'y',
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MMM d'
                            }
                        },
                        position: 'top',
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        labels: medicationNames,
                        title: {
                            display: true,
                            text: 'Medication'
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const medication = medicationNames[context.dataIndex];
                                const start = new Date(startDates[context.dataIndex]).toLocaleDateString();
                                const end = endDates[context.dataIndex] 
                                    ? new Date(endDates[context.dataIndex]).toLocaleDateString() 
                                    : 'Present';
                                return `${medication}: ${start} - ${end}`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Initialize all charts on page load
    initializeSeverityChart();
    initializeMedicationHistoryChart();
});
