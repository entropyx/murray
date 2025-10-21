// Evaluation page JavaScript
let currentFile = null;
let cleanedFilename = null;
let resultsData = null;
let availableLocations = [];
let treatmentLocations = [];
let previewData = null;
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
        reader.readAsText(file);
    }
}

// Clean and process data
async function cleanData() {
    const colDates = document.getElementById('col-dates').value;
    const colLocations = document.getElementById('col-locations').value;
    const colTarget = document.getElementById('col-target').value;

    if (!colDates || !colLocations || !colTarget) {
        showError('Please fill in all column names');
        return;
    }

    if (!currentFile) {
        showError('Please select a file first');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('col_dates', colDates);
        formData.append('col_locations', colLocations);
        formData.append('col_target', colTarget);

        const response = await fetch('/api/data/clean', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to process data');
        }

        cleanedFilename = data.filename;
        availableLocations = data.locations;
        previewData = data.preview;

        // Update UI
        document.getElementById('data-preview').classList.remove('hidden');

        // Populate treatment group dropdown
        const treatmentSelect = document.getElementById('treatment-group-select');
        treatmentSelect.innerHTML = '<option value="">Select location...</option>';
        data.locations.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc;
            option.textContent = loc;
            treatmentSelect.appendChild(option);
        });

        // Add change listener for treatment group selection
        treatmentSelect.onchange = () => {
            const selected = treatmentSelect.value;
            if (selected && !treatmentLocations.includes(selected)) {
                treatmentLocations.push(selected);
                updateTreatmentDisplay();
                treatmentSelect.value = '';
            }
        };

        // Set min/max dates
        const startInput = document.getElementById('start-treatment');
        const endInput = document.getElementById('end-treatment');
        startInput.min = data.date_range.min;
        startInput.max = data.date_range.max;
        endInput.min = data.date_range.min;
        endInput.max = data.date_range.max;
        startInput.value = data.date_range.min;
        endInput.value = data.date_range.max;

        // Render data preview plot (same logic as design.js)
        renderDataPlot(data.preview);

        // Show configuration section
        document.getElementById('configuration-section').classList.remove('hidden');

    } catch (error) {
        showError(error.message);
    }
}

// Update treatment group display
function updateTreatmentDisplay() {
    const container = document.getElementById('treatment-selected');
    const noMsg = document.getElementById('no-treatment-msg');

    if (treatmentLocations.length === 0) {
        noMsg.classList.remove('hidden');
        // Remove all badges
        Array.from(container.children).forEach(child => {
            if (child.id !== 'no-treatment-msg') {
                child.remove();
            }
        });
        return;
    }

    noMsg.classList.add('hidden');

    // Remove all badges (but keep the no-treatment message element)
    Array.from(container.children).forEach(child => {
        if (child.id !== 'no-treatment-msg') {
            child.remove();
        }
    });

    // Add all treatment locations as badges
    treatmentLocations.forEach(loc => {
        const badge = document.createElement('div');
        badge.className = 'flex items-center gap-1 bg-indigo-100 text-indigo-800 px-2 py-1 rounded text-sm';
        badge.innerHTML = `
            <span>${loc}</span>
            <button onclick="removeTreatmentLocation('${loc}')" class="hover:text-indigo-900 font-bold">×</button>
        `;
        container.appendChild(badge);
    });
}

// Remove treatment location
function removeTreatmentLocation(location) {
    treatmentLocations = treatmentLocations.filter(loc => loc !== location);
    updateTreatmentDisplay();
}

// Render data preview plot (same as design.js)
function renderDataPlot(previewData) {
    if (!previewData || previewData.length === 0) {
        document.getElementById('data-plot').innerHTML = '<p class="text-center text-gray-500 py-8">No data available for preview</p>';
        return;
    }

    try {
        // Check if Plotly is loaded
        if (typeof Plotly === 'undefined') {
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

        // Create traces for each location
        const traces = Object.keys(dataByLocation).map(loc => ({
            x: dataByLocation[loc].x,
            y: dataByLocation[loc].y,
            mode: 'lines',
            name: loc,
            type: 'scatter',
            line: { width: 2 }
        }));

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
            height: 500,
            margin: { l: 60, r: 150, t: 50, b: 60 }
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false
        };

        Plotly.newPlot('data-plot', traces, layout, config);
    } catch (error) {
        document.getElementById('data-plot').innerHTML = '<p class="text-center text-red-500 py-8">Error: ' + error.message + '</p>';
    }
}

// Run evaluation
async function runEvaluation() {
    const startTreatment = document.getElementById('start-treatment').value;
    const endTreatment = document.getElementById('end-treatment').value;
    const spend = parseFloat(document.getElementById('spend').value);
    const mmmOption = document.getElementById('mmm-option').value;

    if (!startTreatment || !endTreatment) {
        showError('Please select treatment dates');
        return;
    }

    if (treatmentLocations.length === 0) {
        showError('Please select at least one treatment location');
        return;
    }

    if (!cleanedFilename) {
        showError('Please process data first');
        return;
    }

    try {
        // Show loading
        document.getElementById('results-section').classList.remove('hidden');
        document.getElementById('loading').classList.remove('hidden');
        document.getElementById('results-container').classList.add('hidden');
        document.getElementById('pdf-download-section').classList.add('hidden');

        const response = await fetch('/api/experiment/evaluate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                filename: cleanedFilename,
                start_treatment: startTreatment,
                end_treatment: endTreatment,
                treatment_group: treatmentLocations,
                spend: spend,
                mmm_option: mmmOption
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Evaluation failed');
        }

        // Hide loading
        document.getElementById('loading').classList.add('hidden');

        // Store results
        resultsData = data;

        // Display results
        displayResults(data);

        // Show results container
        document.getElementById('results-container').classList.remove('hidden');
        document.getElementById('pdf-download-section').classList.remove('hidden');

    } catch (error) {
        document.getElementById('loading').classList.add('hidden');
        showError(error.message);
    }
}

// Display results
function displayResults(data) {
    // Update metrics
    document.getElementById('result-lift').textContent = data.percenge_lift.toFixed(2) + '%';
    document.getElementById('result-pvalue').textContent = data.p_value.toFixed(4);
    document.getElementById('result-power').textContent = data.power.toFixed(2);
    document.getElementById('result-control').textContent = data.control_group.join(', ');

    // Use the impact plot from backend (same as Streamlit - no permutation test in UI)
    if (data.impact_plot) {
        // Override height to ensure proper display of 3 subplots
        const impactLayout = {
            ...data.impact_plot.layout,
            height: 900
        };
        Plotly.newPlot('impact-plot', data.impact_plot.data, impactLayout, {responsive: true, displayModeBar: true});
    }
}

// Download PDF report
async function downloadPDFReport() {
    if (!resultsData) {
        showError('No results to download');
        return;
    }

    try {
        const response = await fetch('/api/evaluation/download-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                filename: cleanedFilename,
                start_treatment: document.getElementById('start-treatment').value,
                end_treatment: document.getElementById('end-treatment').value,
                treatment_group: treatmentLocations,
                spend: parseFloat(document.getElementById('spend').value),
                mmm_option: document.getElementById('mmm-option').value,
                results: resultsData
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to generate PDF');
        }

        // Download the PDF
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'murray_evaluation_report.pdf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

    } catch (error) {
        showError(error.message);
    }
}

// Show error message
function showError(message) {
    const errorDiv = document.getElementById('error-display');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    setTimeout(() => {
        errorDiv.classList.add('hidden');
    }, 5000);
}
