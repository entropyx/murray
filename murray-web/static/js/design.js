// Design page JavaScript
let currentFile = null;
let cleanedFilename = null;
let resultsData = null;
let availableLocations = [];
let excludedLocations = [];
let previewData = null;
let currentVizMode = 'apex';
let apexChart = null;
let heatmapData = null;
let resultsFile = null;

// Check authentication
const token = localStorage.getItem('murray_token');
const username = localStorage.getItem('murray_username');

if (!token || !username) {
    window.location.href = '/';
} else {
    document.getElementById('username-display').textContent = username;
}

// Logout function
function logout() {
    localStorage.removeItem('murray_token');
    localStorage.removeItem('murray_username');
    window.location.href = '/';
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

// Remove file
function removeFile() {
    currentFile = null;
    cleanedFilename = null;

    // Reset file input
    document.getElementById('csv-file').value = '';

    // Show upload area and hide file display
    document.getElementById('upload-area').classList.remove('hidden');
    document.getElementById('file-display').classList.add('hidden');

    // Hide other sections
    document.getElementById('column-mapping').classList.add('hidden');
    document.getElementById('data-preview').classList.add('hidden');
    document.getElementById('configuration-section').classList.add('hidden');
    document.getElementById('results-section').classList.add('hidden');
}

// File selection handler
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        currentFile = file;

        // Show file display and hide upload area
        document.getElementById('upload-area').classList.add('hidden');
        document.getElementById('file-display').classList.remove('hidden');
        document.getElementById('file-name').textContent = file.name;
        document.getElementById('file-size').textContent = formatFileSize(file.size);

        document.getElementById('column-mapping').classList.remove('hidden');

        // Try to auto-detect column names from CSV header
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const firstLine = text.split('\n')[0];
            const columns = firstLine.split(',').map(col => col.trim());

            // Auto-fill likely column names
            const dateCol = columns.find(col =>
                /date|time|day|fecha|dia/i.test(col)
            ) || '';
            const locationCol = columns.find(col =>
                /location|region|state|ubicacion/i.test(col)
            ) || '';

            document.getElementById('col-dates').value = dateCol;
            document.getElementById('col-locations').value = locationCol;

            // Set target to first column that's not date or location
            const targetCol = columns.find(col =>
                col !== dateCol && col !== locationCol
            ) || '';
            document.getElementById('col-target').value = targetCol;
        };
        reader.readAsText(file.slice(0, 1000)); // Read first 1KB to get header
    }
}

// Clean data
async function cleanData() {
    if (!currentFile) {
        showError('Please upload a file first');
        return;
    }

    const colDates = document.getElementById('col-dates').value;
    const colLocations = document.getElementById('col-locations').value;
    const colTarget = document.getElementById('col-target').value;

    if (!colDates || !colLocations || !colTarget) {
        showError('Please fill in all column mappings');
        return;
    }

    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('col_dates', colDates);
    formData.append('col_locations', colLocations);
    formData.append('col_target', colTarget);

    try {
        const response = await fetch('/api/data/clean', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            cleanedFilename = data.filename;
            availableLocations = data.locations;
            previewData = data.preview;

            // Update UI
            document.getElementById('data-preview').classList.remove('hidden');

            // Populate excluded locations dropdown
            const excludedSelect = document.getElementById('excluded-locations-select');
            excludedSelect.innerHTML = '<option value="">Select location to exclude...</option>';
            data.locations.forEach(loc => {
                const option = document.createElement('option');
                option.value = loc;
                option.textContent = loc;
                excludedSelect.appendChild(option);
            });

            // Add change handler for excluded locations
            excludedSelect.onchange = handleLocationSelection;

            // Render data preview plot
            renderDataPlot(data.preview);

            // Show configuration section
            document.getElementById('configuration-section').classList.remove('hidden');
            hideError();
        } else {
            showError(data.error || 'Failed to process data');
        }
    } catch (error) {
        showError('Connection error: ' + error.message);
    }
}

// Handle location selection for exclusion
function handleLocationSelection(event) {
    const select = event.target;
    const location = select.value;

    if (location && !excludedLocations.includes(location)) {
        excludedLocations.push(location);
        updateSelectedLocationsDisplay();
        select.value = ''; // Reset dropdown
    }
}

// Remove location from exclusion list
function removeLocation(location) {
    excludedLocations = excludedLocations.filter(loc => loc !== location);
    updateSelectedLocationsDisplay();
}

// Update the visual display of selected locations
function updateSelectedLocationsDisplay() {
    const container = document.getElementById('selected-locations');
    const noSelectionMsg = document.getElementById('no-selection-msg');

    if (excludedLocations.length === 0) {
        container.innerHTML = '<span class="text-xs text-gray-400 italic" id="no-selection-msg">No locations excluded</span>';
    } else {
        container.innerHTML = '';
        excludedLocations.forEach(loc => {
            const badge = document.createElement('span');
            badge.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm bg-murray-primary text-white';
            badge.innerHTML = `
                ${loc}
                <button onclick="removeLocation('${loc}')" class="ml-2 hover:text-gray-200 focus:outline-none">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                    </svg>
                </button>
            `;
            container.appendChild(badge);
        });
    }
}

// Render data plot preview
function renderDataPlot(previewData) {
    console.log('renderDataPlot called with data:', previewData);

    if (!previewData || previewData.length === 0) {
        console.error('No preview data available');
        document.getElementById('data-plot').innerHTML = '<p class="text-center text-gray-500 py-8">No data available for preview</p>';
        return;
    }

    try {
        // Check if Plotly is loaded
        if (typeof Plotly === 'undefined') {
            console.error('Plotly not loaded');
            document.getElementById('data-plot').innerHTML = '<p class="text-center text-red-500 py-8">Visualization library not loaded</p>';
            return;
        }

        // Group data by location
        const dataByLocation = {};
        previewData.forEach(row => {
            const loc = row.location;
            if (!dataByLocation[loc]) {
                dataByLocation[loc] = { x: [], y: [] };
            }
            dataByLocation[loc].x.push(row.time);
            dataByLocation[loc].y.push(row.target);
        });

        console.log('Data grouped by location:', Object.keys(dataByLocation));

        // Create traces for each location
        const traces = Object.keys(dataByLocation).map(loc => ({
            x: dataByLocation[loc].x,
            y: dataByLocation[loc].y,
            mode: 'lines',
            name: loc,
            type: 'scatter',
            line: { width: 2 },
            marker: { size: 4 }
        }));

        console.log('Created traces:', traces.length);

        const layout = {
            title: 'Data visualization by Location',
            xaxis: {
                title: 'Time',
                type: 'date'
            },
            yaxis: {
                title: 'Target Metric'
            },
            showlegend: true,
            legend: {
                orientation: 'v',
                x: 1.02,
                y: 1,
                xanchor: 'left'
            },
            hovermode: 'closest',
            margin: { l: 60, r: 150, t: 50, b: 60 }
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false
        };

        Plotly.newPlot('data-plot', traces, layout, config)
            .then(() => console.log('Data plot rendered successfully'))
            .catch(err => {
                console.error('Error rendering data plot:', err);
                document.getElementById('data-plot').innerHTML = '<p class="text-center text-red-500 py-8">Error rendering plot: ' + err.message + '</p>';
            });
    } catch (error) {
        console.error('Exception in renderDataPlot:', error);
        document.getElementById('data-plot').innerHTML = '<p class="text-center text-red-500 py-8">Error: ' + error.message + '</p>';
    }
}

// Run analysis
async function runAnalysis() {
    if (!cleanedFilename) {
        showError('Please process data first');
        return;
    }

    // Get configuration values
    const config = {
        filename: cleanedFilename,
        excluded_locations: excludedLocations,
        maximum_treatment_percentage: parseInt(document.getElementById('max-treatment').value) / 100,
        significance_level: parseInt(document.getElementById('significance-level').value) / 100,
        delta_min: parseFloat(document.getElementById('delta-min').value),
        delta_max: parseFloat(document.getElementById('delta-max').value),
        delta_step: parseFloat(document.getElementById('delta-step').value),
        period_min: parseInt(document.getElementById('period-min').value),
        period_max: parseInt(document.getElementById('period-max').value),
        period_step: parseInt(document.getElementById('period-step').value),
        test_type: 'sum'
    };

    // Validation
    if (config.delta_min >= config.delta_max) {
        showError('Delta min must be less than delta max');
        return;
    }
    if (config.period_min >= config.period_max) {
        showError('Period min must be less than period max');
        return;
    }

    // Show loading
    document.getElementById('results-section').classList.remove('hidden');
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('heatmap-container').classList.add('hidden');
    document.getElementById('point-details').classList.add('hidden');
    document.getElementById('run-btn').disabled = true;
    document.getElementById('run-btn').textContent = 'Running...';
    hideError();

    try {
        const response = await fetch('/api/experiment/design', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            resultsData = data;
            heatmapData = data.heatmap;
            resultsFile = data.results_file;

            // Hide loading
            document.getElementById('loading').classList.add('hidden');

            // Show heatmap and PDF download button
            document.getElementById('heatmap-container').classList.remove('hidden');
            document.getElementById('pdf-download-section').classList.remove('hidden');
            renderHeatmap(data.heatmap);
        } else {
            showError(data.error || 'Analysis failed');
            document.getElementById('loading').classList.add('hidden');
        }
    } catch (error) {
        showError('Connection error: ' + error.message);
        document.getElementById('loading').classList.add('hidden');
    } finally {
        document.getElementById('run-btn').disabled = false;
        document.getElementById('run-btn').textContent = 'Run Simulation';
    }
}

// Render heatmap (delegates to current visualization mode)
function renderHeatmap(data) {
    heatmapData = data;

    // Render ApexCharts by default
    renderApexHeatmap(data);

    // Show color scale for ApexCharts
    document.getElementById('apex-color-scale').style.display = 'flex';
}

// Handle heatmap click
function handleHeatmapClick(point) {
    console.log('handleHeatmapClick called with point:', point);

    if (!resultsData || !resultsData.simulation_results || !resultsData.sensitivity_results) {
        console.error('Results data not available');
        showError('Results data not loaded properly');
        return;
    }

    const xValue = point.x; // Period (e.g., "Day-15" or just number)
    const yValue = point.y; // Holdout percentage (e.g., "25.50%" or number)

    console.log('xValue:', xValue, 'yValue:', yValue);

    // Extract period number (handle both "Day-15" and just "15")
    let period;
    if (typeof xValue === 'string') {
        period = parseInt(xValue.replace(/Day-|days?/gi, '').trim());
    } else {
        period = parseInt(xValue);
    }

    // Extract holdout percentage (handle both "25.50%" and just 25.50)
    let holdoutPct;
    if (typeof yValue === 'string') {
        holdoutPct = parseFloat(yValue.replace('%', '').trim());
    } else {
        holdoutPct = parseFloat(yValue);
    }

    console.log('Parsed - period:', period, 'holdoutPct:', holdoutPct);

    // Find matching simulation result
    let matchingSize = null;
    let bestMatch = null;
    let minDiff = Infinity;

    for (const [size, result] of Object.entries(resultsData.simulation_results)) {
        const diff = Math.abs(result.holdout_percentage - holdoutPct);
        console.log(`Checking size ${size}: holdout=${result.holdout_percentage}, diff=${diff}`);

        if (diff < minDiff) {
            minDiff = diff;
            bestMatch = size;
        }

        // Exact or very close match
        if (diff < 0.1) {
            matchingSize = size;
            break;
        }
    }

    // If no exact match, use best match
    if (!matchingSize && bestMatch) {
        matchingSize = bestMatch;
        console.log('Using best match:', matchingSize, 'with diff:', minDiff);
    }

    console.log('Matching size:', matchingSize);

    if (matchingSize && resultsData.sensitivity_results[matchingSize]) {
        const simResult = resultsData.simulation_results[matchingSize];
        const sensResult = resultsData.sensitivity_results[matchingSize][period.toString()];

        console.log('simResult:', simResult);
        console.log('sensResult:', sensResult);

        if (sensResult && sensResult.mde !== undefined) {
            // Display details
            document.getElementById('point-details').classList.remove('hidden');

            const treatmentGroup = Array.isArray(simResult.treatment_group)
                ? simResult.treatment_group.join(', ')
                : simResult.treatment_group || 'N/A';
            const controlGroup = Array.isArray(simResult.control_group)
                ? simResult.control_group.join(', ')
                : simResult.control_group || 'N/A';

            document.getElementById('detail-treatment').textContent = treatmentGroup;
            document.getElementById('detail-control').textContent = controlGroup;

            // MDE
            const mde = sensResult.MDE || sensResult.mde;
            document.getElementById('detail-mde').textContent = mde !== undefined && mde !== null
                ? (mde * 100).toFixed(1) + '%'
                : 'N/A';

            // Power
            const power = sensResult.Power || sensResult.power;
            document.getElementById('detail-power').textContent = power !== undefined && power !== null
                ? (power * 100).toFixed(1) + '%'
                : 'N/A';

            // P-Value (check multiple possible field names)
            const pValue = sensResult['P-Value'] || sensResult.p_value || sensResult.pValue || sensResult.pvalue;
            document.getElementById('detail-pvalue').textContent = pValue !== undefined && pValue !== null
                ? pValue.toFixed(4)
                : 'N/A';

            document.getElementById('detail-holdout').textContent = holdoutPct.toFixed(2) + '%';

            // Scroll to details
            document.getElementById('point-details').scrollIntoView({ behavior: 'smooth' });

            console.log('Details displayed successfully');
        } else {
            console.error('Sensitivity result not found or incomplete for period:', period);
            showError(`No data available for period ${period}`);
        }
    } else {
        console.error('No matching size found or sensitivity results missing');
        showError(`No matching data found for holdout ${holdoutPct.toFixed(2)}%`);
    }
}

// Error handling
function showError(message) {
    const errorDiv = document.getElementById('error-display');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    errorDiv.scrollIntoView({ behavior: 'smooth' });
}

function hideError() {
    document.getElementById('error-display').classList.add('hidden');
}

// Switch visualization mode
function switchVizMode(mode) {
    currentVizMode = mode;

    // Update button styles
    ['apex', 'plotly', 'table'].forEach(m => {
        const btn = document.getElementById(`viz-mode-${m}`);
        if (m === mode) {
            btn.className = 'px-4 py-2 rounded-lg bg-murray-primary text-white';
        } else {
            btn.className = 'px-4 py-2 rounded-lg bg-gray-200 text-gray-700';
        }
    });

    // Hide all visualizations
    document.getElementById('heatmap-apex').style.display = 'none';
    document.getElementById('heatmap-plotly').style.display = 'none';
    document.getElementById('heatmap-table').classList.add('hidden');
    document.getElementById('apex-color-scale').style.display = 'none';

    // Show selected visualization
    if (mode === 'apex') {
        document.getElementById('heatmap-apex').style.display = 'block';
        document.getElementById('apex-color-scale').style.display = 'flex';
        if (!apexChart && heatmapData) {
            renderApexHeatmap(heatmapData);
        }
    } else if (mode === 'plotly') {
        document.getElementById('heatmap-plotly').style.display = 'block';
        if (heatmapData) {
            renderPlotlyHeatmap(heatmapData);
        }
    } else if (mode === 'table') {
        document.getElementById('heatmap-table').classList.remove('hidden');
        if (heatmapData) {
            renderTableHeatmap(heatmapData);
        }
    }
}

// Render ApexCharts heatmap
function renderApexHeatmap(data) {
    try {
        if (typeof ApexCharts === 'undefined') {
            console.error('ApexCharts not loaded');
            document.getElementById('heatmap-apex').innerHTML = '<p class="text-center text-red-500 py-8">ApexCharts library not loaded</p>';
            return;
        }

        // Extract data from Plotly format
        const plotlyData = data.data[0];
        const periods = plotlyData.x || [];
        const sizes = plotlyData.y || [];
        const values = plotlyData.z || [];

        // Find min and max values in the data
        let minValue = Infinity;
        let maxValue = -Infinity;
        for (let i = 0; i < values.length; i++) {
            for (let j = 0; j < values[i].length; j++) {
                const val = values[i][j];
                if (val !== null && val !== undefined) {
                    minValue = Math.min(minValue, val);
                    maxValue = Math.max(maxValue, val);
                }
            }
        }

        console.log('Data range: min =', minValue, 'max =', maxValue);

        // Convert to ApexCharts series format
        const series = [];
        for (let i = 0; i < sizes.length; i++) {
            const rowData = [];
            for (let j = 0; j < periods.length; j++) {
                rowData.push({
                    x: periods[j],
                    y: values[i] ? values[i][j] : 0
                });
            }
            series.push({
                name: sizes[i],
                data: rowData
            });
        }

        // Use exact same colorscale as Plotly: Green (#84DA35) to Red (#DA3835)
        // Generate gradient with 10 steps between these colors
        const range = maxValue - minValue;
        const step = range / 10;

        // Interpolate between green and red
        function interpolateColor(ratio) {
            const green = { r: 0x84, g: 0xDA, b: 0x35 };
            const red = { r: 0xDA, g: 0x38, b: 0x35 };
            const r = Math.round(green.r + (red.r - green.r) * ratio);
            const g = Math.round(green.g + (red.g - green.g) * ratio);
            const b = Math.round(green.b + (red.b - green.b) * ratio);
            return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
        }

        const colorRanges = [];
        for (let i = 0; i < 10; i++) {
            const fromVal = minValue + step * i;
            const toVal = minValue + step * (i + 1);
            colorRanges.push({
                from: fromVal,
                to: toVal,
                color: interpolateColor(i / 9),
                name: `${(fromVal * 100).toFixed(1)}-${(toVal * 100).toFixed(1)}%`
            });
        }

        const options = {
            series: series,
            chart: {
                height: 600,
                type: 'heatmap',
                toolbar: {
                    show: true
                },
                events: {
                    click: function(event, chartContext, config) {
                        if (config.dataPointIndex >= 0 && config.seriesIndex >= 0) {
                            const period = periods[config.dataPointIndex];
                            const size = sizes[config.seriesIndex];
                            handleHeatmapClick({ x: period, y: size });
                        }
                    }
                }
            },
            dataLabels: {
                enabled: true,
                style: {
                    colors: ['#000'],
                    fontSize: '13px',
                    fontWeight: 600
                },
                formatter: function(value) {
                    return (value * 100).toFixed(2) + '%';
                }
            },
            colors: ['#4f46e5'],
            title: {
                text: 'Minimum Detectable Effect (MDE) by Period and Group Size'
            },
            xaxis: {
                title: {
                    text: 'Treatment Period (Days)'
                }
            },
            yaxis: {
                title: {
                    text: 'Holdout Percentage (%)'
                }
            },
            plotOptions: {
                heatmap: {
                    shadeIntensity: 0,  // 0 = sin sombreado, colores puros como Plotly
                    radius: 0,  // 0 = celdas cuadradas sin bordes redondeados
                    useFillColorAsStroke: false,
                    enableShades: false,  // Deshabilitar sombreados
                    distributed: false,
                    colorScale: {
                        ranges: colorRanges,
                        inverse: false,
                        min: minValue,
                        max: maxValue
                    }
                }
            },
            tooltip: {
                style: {
                    fontSize: '14px',
                    fontFamily: undefined
                },
                y: {
                    formatter: function(value) {
                        return (value * 100).toFixed(1) + '%';
                    }
                }
            },
            legend: {
                show: false  // Hide the confusing legend with decimal values
            }
        };

        if (apexChart) {
            apexChart.destroy();
        }

        apexChart = new ApexCharts(document.querySelector('#heatmap-apex'), options);
        apexChart.render();

        console.log('ApexCharts heatmap rendered successfully');

    } catch (error) {
        console.error('Error rendering ApexCharts heatmap:', error);
        document.getElementById('heatmap-apex').innerHTML = '<p class="text-center text-red-500 py-8">Error: ' + error.message + '</p>';
    }
}

// Render Plotly heatmap
function renderPlotlyHeatmap(data) {
    try {
        if (typeof Plotly === 'undefined') {
            console.error('Plotly not loaded');
            document.getElementById('heatmap-plotly').innerHTML = '<p class="text-center text-red-500 py-8">Plotly library not loaded</p>';
            return;
        }

        const layout = {
            title: 'Minimum Detectable Effect (MDE) by Period and Group Size',
            xaxis: {
                title: 'Treatment Period (Days)',
                tickangle: -45
            },
            yaxis: {
                title: 'Holdout Percentage (%)',
                autorange: 'reversed'
            },
            hovermode: 'closest',
            height: 600,
            ...data.layout
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
        };

        Plotly.newPlot('heatmap-plotly', data.data, layout, config).then(() => {
            console.log('Plotly heatmap rendered successfully');

            const heatmapDiv = document.getElementById('heatmap-plotly');

            // Remove any existing listeners
            heatmapDiv.removeAllListeners && heatmapDiv.removeAllListeners('plotly_click');

            // Add click event listener
            heatmapDiv.on('plotly_click', function(eventData) {
                console.log('Plotly click event fired:', eventData);

                if (eventData.points && eventData.points.length > 0) {
                    const point = eventData.points[0];
                    console.log('Point clicked:', point);

                    // Call the handler
                    handleHeatmapClick(point);
                } else {
                    console.warn('No points in click event');
                }
            });

            console.log('Plotly click handler attached');
        }).catch(err => {
            console.error('Error rendering Plotly heatmap:', err);
            document.getElementById('heatmap-plotly').innerHTML = '<p class="text-center text-red-500 py-8">Error: ' + err.message + '</p>';
        });

    } catch (error) {
        console.error('Plotly heatmap rendering error:', error);
        document.getElementById('heatmap-plotly').innerHTML = '<p class="text-center text-red-500 py-8">Error: ' + error.message + '</p>';
    }
}

// Render table heatmap
function renderTableHeatmap(data) {
    try {
        const plotlyData = data.data[0];
        const periods = plotlyData.x || [];
        const sizes = plotlyData.y || [];
        const values = plotlyData.z || [];

        let html = '<table class="w-full border-collapse"><thead><tr class="bg-gray-100">';
        html += '<th class="border border-gray-300 px-2 py-2 text-xs font-semibold">Size / Period</th>';

        periods.forEach(period => {
            html += `<th class="border border-gray-300 px-2 py-2 text-xs font-semibold">${period}</th>`;
        });
        html += '</tr></thead><tbody>';

        sizes.forEach((size, i) => {
            html += '<tr>';
            html += `<td class="border border-gray-300 px-2 py-2 text-xs font-semibold bg-gray-50">${size}</td>`;

            periods.forEach((period, j) => {
                const value = values[i] ? values[i][j] : 0;
                const percentage = (value * 100).toFixed(1);

                // Color coding
                let bgColor = 'bg-green-100';
                if (value > 0.10) bgColor = 'bg-red-100';
                else if (value > 0.05) bgColor = 'bg-yellow-100';

                html += `<td class="border border-gray-300 px-2 py-2 text-xs text-center ${bgColor} cursor-pointer hover:bg-opacity-70"
                         onclick="handleHeatmapClick({x: '${period}', y: '${size}'})">${percentage}%</td>`;
            });

            html += '</tr>';
        });

        html += '</tbody></table>';

        document.getElementById('heatmap-table').innerHTML = html;

        console.log('Table heatmap rendered successfully');

    } catch (error) {
        console.error('Error rendering table heatmap:', error);
        document.getElementById('heatmap-table').innerHTML = '<p class="text-center text-red-500 py-8">Error: ' + error.message + '</p>';
    }
}

// Download PDF Report
async function downloadPDFReport() {
    if (!resultsData) {
        showError('No results available to generate report');
        return;
    }

    const btn = document.getElementById('pdf-download-btn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="inline-block w-5 h-5 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Generating PDF...';

    try {
        const response = await fetch('/api/experiment/download-pdf', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: resultsData,
                filename: cleanedFilename,
                results_file: resultsFile
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'murray_experimental_design_report.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            console.log('PDF downloaded successfully');
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to generate PDF');
        }
    } catch (error) {
        showError('Error downloading PDF: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg class="inline-block w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>Download PDF Report';
    }
}
