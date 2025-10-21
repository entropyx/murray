"""
Murray Web UI - Flask Backend
Thin wrapper around existing Murray library functions
"""
from flask import Flask, request, jsonify, send_file, send_from_directory, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta
import jwt
from functools import wraps

# Add parent directory to path to import Murray
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Murray.main import run_geo_analysis_streamlit_app, transform_results_data
from Murray.post_analysis import run_geo_evaluation
from Murray.auxiliary import cleaned_data
from Murray.plots import plot_geodata, plot_mde_results, plot_impact_report, print_weights, plot_impact_evaluation_streamlit
from utils_auth import check_credentials, add_user
import numpy as np

# Import PDF generation (use original from experimental_design)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from experimental_design import generate_pdf
import pickle

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'murray-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

CORS(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# JWT token decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['username']
        except:
            return jsonify({'error': 'Token is invalid'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# Serve static HTML pages
@app.route('/')
def index():
    return send_from_directory('templates', 'login.html')


@app.route('/design')
def design_page():
    return send_from_directory('templates', 'design.html')


@app.route('/evaluation')
def evaluation_page():
    return send_from_directory('templates', 'evaluation.html')


# Authentication endpoints
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint using existing authentication"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    # Check if entropy email (auto-approve)
    is_entropy_email = username.strip().endswith("@entropy.tech")

    if is_entropy_email or check_credentials(username, password):
        # Generate JWT token
        token = jwt.encode({
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'success': True,
            'token': token,
            'username': username
        })

    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    registration_token = data.get('registration_token', '')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    success, message = add_user(username, password, registration_token=registration_token)

    if success:
        return jsonify({'success': True, 'message': message})

    return jsonify({'error': message}), 400


# Data processing endpoints
@app.route('/api/data/clean', methods=['POST'])
@token_required
def clean_data(current_user):
    """Clean and prepare data for analysis"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Read CSV
        df = pd.read_csv(file)

        # Get column mappings from form data
        col_dates = request.form.get('col_dates')
        col_locations = request.form.get('col_locations')
        col_target = request.form.get('col_target')

        if not all([col_dates, col_locations, col_target]):
            return jsonify({'error': 'All column mappings required'}), 400

        # Clean data using Murray function
        cleaned = cleaned_data(
            df,
            col_dates=col_dates,
            col_locations=col_locations,
            col_target=col_target
        )

        # Save cleaned data temporarily (use session ID for unique filename)
        filename = f"cleaned_{current_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cleaned.to_csv(filepath, index=False)

        # Get available locations
        locations = cleaned['location'].unique().tolist()

        # Get data preview for plot - include ALL locations and ALL data points
        preview_list = []
        for _, row in cleaned.iterrows():
            preview_list.append({
                'location': row['location'],
                'time': row['time'].strftime('%Y-%m-%d') if hasattr(row['time'], 'strftime') else str(row['time']),
                'target': float(row['Y'])  # Column is renamed to 'Y' by cleaned_data
            })

        # Get date range
        min_date = cleaned['time'].min().strftime('%Y-%m-%d')
        max_date = cleaned['time'].max().strftime('%Y-%m-%d')

        return jsonify({
            'success': True,
            'filename': filename,
            'preview': preview_list,
            'locations': locations,
            'date_range': {'min': min_date, 'max': max_date},
            'total_rows': len(cleaned),
            'total_locations': len(locations)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/experiment/design', methods=['POST'])
@token_required
def run_design(current_user):
    """Run experimental design analysis"""
    try:
        data = request.json
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': 'No data file specified'}), 400

        # Load cleaned data
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Data file not found'}), 404

        cleaned = pd.read_csv(filepath)
        cleaned['time'] = pd.to_datetime(cleaned['time'])

        # Get parameters from request
        excluded_locations = data.get('excluded_locations', [])
        excluded_from_control = data.get('excluded_from_control', [])
        maximum_treatment_percentage = data.get('maximum_treatment_percentage', 0.3)
        significance_level = data.get('significance_level', 0.05)

        # Delta range (lift)
        delta_min = data.get('delta_min', 0.01)
        delta_max = data.get('delta_max', 0.15)
        delta_step = data.get('delta_step', 0.01)
        deltas_range = (delta_min, delta_max, delta_step)

        # Period range
        period_min = data.get('period_min', 5)
        period_max = data.get('period_max', 30)
        period_step = data.get('period_step', 5)
        periods_range = (period_min, period_max + 1, period_step)

        test_type = data.get('test_type', 'sum')

        # Run analysis using Murray function
        results = run_geo_analysis_streamlit_app(
            data=cleaned,
            excluded_locations=excluded_locations,
            excluded_from_control=excluded_from_control,
            maximum_treatment_percentage=maximum_treatment_percentage,
            significance_level=significance_level,
            deltas_range=deltas_range,
            periods_range=periods_range,
            test_type=test_type,
            inference_type='iid',
            global_optimization=False
        )

        if results is None:
            return jsonify({'error': 'Analysis failed to find valid treatment/control groups'}), 400

        # Transform results
        results_by_size = transform_results_data(results['simulation_results'])

        # Save full results for PDF generation later
        results_filename = f"results_{current_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        results_filepath = os.path.join(app.config['UPLOAD_FOLDER'], results_filename)
        import pickle
        with open(results_filepath, 'wb') as f:
            pickle.dump({
                'results': results,
                'results_by_size': results_by_size,
                'periods_range': periods_range,
                'significance_level': significance_level
            }, f)

        # Prepare response (convert numpy/pandas to JSON-serializable formats)
        response = {
            'success': True,
            'simulation_results': {},
            'sensitivity_results': {},
            'results_file': results_filename  # Store filename for PDF generation
        }

        # Convert simulation results
        for size, data in results_by_size.items():
            response['simulation_results'][str(size)] = {
                'treatment_group': data['Best Treatment Group'],
                'control_group': data['Control Group'],
                'smape': float(data['SMAPE']),
                'holdout_percentage': float(data['Holdout Percentage'])
            }

        # Convert sensitivity results
        for size, periods in results['sensitivity_results'].items():
            response['sensitivity_results'][str(size)] = {}
            for period, metrics in periods.items():
                response['sensitivity_results'][str(size)][str(period)] = {
                    'mde': float(metrics['MDE']),
                    'p_value': float(metrics['P-Value']),
                    'power': float(metrics.get('Power', 0))
                }

        # Generate heatmap data (for Plotly.js)
        periods = list(np.arange(*periods_range))
        fig = plot_mde_results(results_by_size, results['sensitivity_results'], periods)
        response['heatmap'] = json.loads(fig.to_json())

        return jsonify(response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/experiment/download-pdf', methods=['POST'])
@token_required
def download_pdf(current_user):
    """Generate and download comprehensive PDF report like Streamlit"""
    try:
        data = request.json
        results_file = data.get('results_file')
        filename = data.get('filename')

        if not results_file:
            return jsonify({'error': 'No results file specified'}), 400

        # Load saved results
        results_filepath = os.path.join(app.config['UPLOAD_FOLDER'], results_file)
        if not os.path.exists(results_filepath):
            return jsonify({'error': 'Results file not found'}), 404

        with open(results_filepath, 'rb') as f:
            saved_data = pickle.load(f)

        results = saved_data['results']
        results_by_size = saved_data['results_by_size']
        periods_range = saved_data['periods_range']
        significance_level = saved_data['significance_level']

        # Load cleaned data
        data_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cleaned = pd.read_csv(data_filepath)
        cleaned['time'] = pd.to_datetime(cleaned['time'])

        # Get the first/best size configuration
        first_size = list(results_by_size.keys())[0]
        sim_result = results_by_size[first_size]

        treatment_group = sim_result['Best Treatment Group']
        control_group = sim_result['Control Group']
        holdout_percentage = sim_result['Holdout Percentage']

        # Get period and MDE
        period_idx = periods_range[0]  # First period
        mde = None
        p_value = None
        power_value = None

        if first_size in results['sensitivity_results']:
            if period_idx in results['sensitivity_results'][first_size]:
                mde = results['sensitivity_results'][first_size][period_idx]['MDE']
                p_value = results['sensitivity_results'][first_size][period_idx].get('P-Value')
                power_value = results['sensitivity_results'][first_size][period_idx].get('Power')

        # Get weights
        weights = print_weights(results, holdout_percentage / 100)

        # Generate impact visualization
        length_treatment = len(treatment_group.split(','))
        (
            pre_treatment,
            pre_counterfactual,
            post_treatment,
            post_counterfactual,
            impact_graph,
            att,
            incremental,
            lower_bound_value,
            upper_bound_value,
            prediction_value,
        ) = plot_impact_report(
            results,
            period_idx,
            holdout_percentage,
            length_treatment,
            significance_level,
        )

        # Calculate values for PDF
        prediction_value_absolute = prediction_value
        prediction_value_percentage = (
            (prediction_value - np.sum(post_counterfactual))
            / np.abs(np.sum(post_counterfactual))
            * 100
        )
        lower_bound_value_absolute = lower_bound_value
        lower_bound_value_percentage = (
            (lower_bound_value - np.sum(post_counterfactual))
            / np.abs(np.sum(post_counterfactual))
            * 100
        )
        upper_bound_value_absolute = upper_bound_value
        upper_bound_value_percentage = (
            (upper_bound_value - np.sum(post_counterfactual))
            / np.abs(np.sum(post_counterfactual))
            * 100
        )

        # Create comparison dataframe
        comparison_df = pd.DataFrame(
            {
                "Group": [
                    "Treatment",
                    "Counterfactual (control)",
                    "Absolute difference",
                ],
                "Pre-treatment": [
                    np.sum(pre_treatment),
                    np.sum(pre_counterfactual),
                    np.abs(np.sum(pre_treatment) - np.sum(pre_counterfactual)),
                ],
                "Post-treatment": [
                    np.sum(post_treatment),
                    np.sum(post_counterfactual),
                    np.abs(np.sum(post_treatment) - np.sum(post_counterfactual)),
                ],
            }
        )

        # Get date information
        firt_day = cleaned['time'].min().strftime('%Y-%m-%d')
        last_day = cleaned['time'].max().strftime('%Y-%m-%d')
        treatment_day = cleaned['time'].min().strftime('%Y-%m-%d')  # Placeholder
        col_target = 'target'  # Or get from request
        confidence_level = 1 - significance_level
        firt_report_day = firt_day
        second_report_day = last_day

        # Generate PDF with all parameters
        pdf_path = generate_pdf(
            treatment_group=treatment_group,
            control_group=control_group,
            holdout_percentage=holdout_percentage,
            impact_graph=impact_graph,
            weights=weights,
            period_idx=period_idx,
            mde=mde,
            att=att,
            incremental=incremental,
            tarjet_variable=col_target,
            firt_day=firt_day,
            last_day=last_day,
            treatment_day=treatment_day,
            df=comparison_df,
            firt_report_day=firt_report_day,
            second_report_day=second_report_day,
            prediction_value_absolute=prediction_value_absolute,
            prediction_value_percentage=prediction_value_percentage,
            lower_bound_value_absolute=lower_bound_value_absolute,
            lower_bound_value_percentage=lower_bound_value_percentage,
            upper_bound_value_absolute=upper_bound_value_absolute,
            upper_bound_value_percentage=upper_bound_value_percentage,
            confidence_level=confidence_level,
            p_value=p_value,
            power_value=power_value,
        )

        # Send PDF file
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='murray_experimental_design_report.pdf'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/experiment/evaluate', methods=['POST'])
@token_required
def run_evaluation(current_user):
    """Run experimental evaluation"""
    try:
        data = request.json
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': 'No data file specified'}), 400

        # Load cleaned data
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Data file not found'}), 404

        cleaned = pd.read_csv(filepath)
        cleaned['time'] = pd.to_datetime(cleaned['time'])

        # Get parameters
        start_treatment = pd.to_datetime(data.get('start_treatment'))
        end_treatment = pd.to_datetime(data.get('end_treatment'))
        treatment_group = data.get('treatment_group', [])
        spend = float(data.get('spend', 0))

        # Run evaluation using Murray function
        results = run_geo_evaluation(
            cleaned,
            start_treatment,
            end_treatment,
            treatment_group,
            spend
        )

        # Get first location to extract dates
        random_state = cleaned["location"].unique()[0]
        filtered_data = cleaned[cleaned["location"] == random_state]

        # Generate impact evaluation plot (returns tuple: fig, att, incremental, lower, upper, prediction)
        length_treatment = len(treatment_group)
        impact_result = plot_impact_evaluation_streamlit(results, filtered_data, length_treatment)
        impact_fig = impact_result[0]  # Extract figure from tuple

        att = impact_result[1]
        incremental = impact_result[2]
        lower_bound = impact_result[3]
        upper_bound = impact_result[4]
        prediction_value = impact_result[5]

        # Prepare response with plotly figure (convert all numeric types to native Python)
        # Note: Only impact_plot is shown in Streamlit UI, permutation test is only for PDF
        # Manually build the JSON from the figure object to avoid compression
        impact_plot_json = {
            'data': [],
            'layout': impact_fig.layout.to_plotly_json()
        }

        # Convert each trace manually from the figure object (before dict conversion)
        for trace in impact_fig.data:
            trace_dict = {}
            # Copy essential properties and convert to JSON-safe format
            for key in ['type', 'name', 'mode', 'showlegend', 'fill', 'fillcolor', 'hovertext', 'hoverinfo', 'xaxis', 'yaxis']:
                if hasattr(trace, key):
                    val = getattr(trace, key)
                    if val is not None:
                        trace_dict[key] = val

            # Handle line object separately (convert to dict)
            if hasattr(trace, 'line') and trace.line is not None:
                if hasattr(trace.line, 'to_plotly_json'):
                    trace_dict['line'] = trace.line.to_plotly_json()
                elif isinstance(trace.line, dict):
                    trace_dict['line'] = trace.line

            # Convert x and y arrays manually
            if hasattr(trace, 'x') and trace.x is not None:
                trace_dict['x'] = [str(v) for v in trace.x]
            if hasattr(trace, 'y') and trace.y is not None:
                trace_dict['y'] = [float(v) for v in trace.y]

            impact_plot_json['data'].append(trace_dict)

        response = {
            'success': True,
            'treatment': results['treatment'].tolist(),
            'counterfactual': results['counterfactual'].tolist(),
            'p_value': float(results['p_value']),
            'power': float(results['power']),
            'percenge_lift': float(results['percenge_lift']),
            'control_group': results['control_group'],
            'observed_stat': float(results['observed_stat']),
            'null_stats': results['null_stats'].tolist() if hasattr(results['null_stats'], 'tolist') else results['null_stats'],
            'impact_plot': impact_plot_json,
            'att': float(att),
            'incremental': float(incremental),
            'lower_bound': float(lower_bound),
            'upper_bound': float(upper_bound),
            'prediction_value': float(prediction_value)
        }

        return jsonify(response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/download-pdf', methods=['POST'])
@token_required
def download_evaluation_pdf(current_user):
    """Generate and download PDF report for evaluation"""
    try:
        data = request.json
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': 'No data file specified'}), 400

        # Load cleaned data
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Data file not found'}), 404

        # This endpoint will be implemented when PDF generation for evaluation is ready
        # For now, return a placeholder
        return jsonify({'error': 'PDF generation for evaluation is not yet implemented'}), 501

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'murray-web'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
