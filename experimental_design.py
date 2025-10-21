# Streamlit app for experimental design workflow: upload data, configure parameters, run simulation, generate reports
import streamlit as st
import pandas as pd
from Murray.main import run_geo_analysis_streamlit_app, transform_results_data
from logger_config import get_logger

app_logger = get_logger("experimental_design")
from Murray.auxiliary import (
    cleaned_data,
    analyze_data_characteristics,
    get_test_explanation,
)
from Murray.plots import *
from streamlit_js_eval import streamlit_js_eval
from fpdf import FPDF
import base64
import os
from Murray.metrics import update_metrics, load_metrics
import unicodedata
import plotly.express as px
import numpy as np


# App branding and logos
ENTROPY_LOGO = "utils/Logo Entropy Dark Gray.png"
MURRAY_LOGO = "utils/Group 105.png"
options = [ENTROPY_LOGO, MURRAY_LOGO]
sidebar_logo = ENTROPY_LOGO
main_body_logo = MURRAY_LOGO

# Setup sidebar with documentation link
st.sidebar.markdown(
    """
    <style>
    .custom-link {
        color: #211F24 !important;  
        text-decoration: none;  
        display: block;
        padding: 5px;
        border-radius: 5px;
    }
    .custom-link:hover {
        color: #3e7cb1 !important;  
    }
    </style>
    <a class='custom-link' href="https://docs-murray.entropy.tech/" target="_blank">Murray Documentation</a>
    """,
    unsafe_allow_html=True,
)


# Configure app logos
st.logo(sidebar_logo, size="large", icon_image=main_body_logo)


# Generate PDF report with experimental design results
def generate_pdf(
    treatment_group,
    control_group,
    holdout_percentage,
    impact_graph,
    weights,
    period_idx,
    mde,
    att,
    incremental,
    tarjet_variable,
    firt_day,
    last_day,
    treatment_day,
    df,
    firt_report_day,
    second_report_day,
    prediction_value_absolute,
    prediction_value_percentage,
    lower_bound_value_absolute,
    lower_bound_value_percentage,
    upper_bound_value_absolute,
    upper_bound_value_percentage,
    confidence_level,
    p_value=None,
    power_value=None,
    avg_scaled_l2=None,
    smape_value=None,
):
    temp_image_path = "temp_impact_graph.png"
    impact_graph.savefig(temp_image_path, bbox_inches="tight", dpi=100)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.add_font("Poppins", style="B", fname="utils/Poppins-Bold.ttf", uni=True)
    pdf.add_font("Poppins", "", "utils/Poppins-Regular.ttf", uni=True)

    pdf.image("utils/Logo Entropy Dark Gray.png", x=10, y=10, w=20)
    pdf.set_font("Poppins", style="B", size=20)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 10, "Geo Murray Report", ln=True, align="C")

    y_actual = pdf.get_y() + 2
    pdf.line(10, y_actual, 200, y_actual)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(7)

    pdf.set_font("Poppins", size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(
        0,
        5,
        f"This report provides information about the experimental design on the variable '{tarjet_variable}', "
        f"the experimental design was conducted for a duration of {period_idx} days. "
        f"The data included in the design have a period of {firt_day} to {last_day} where the treatment "
        f"started on {treatment_day} until {last_day}. It includes information about the treatment group, "
        f"control group, minimum detectable effect (MDE), and other relevant information.",
    )
    pdf.ln(5)

    pdf.set_font("Poppins", style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 8, "Treatment Group:", ln=True)
    pdf.set_font("Poppins", size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(
        0,
        5,
        "The treatment group consists of individuals or units that received the experimental intervention or treatment. "
        "The following is the description of the treatment group: ",
    )
    pdf.set_font("Poppins", style="B", size=9.5)
    pdf.multi_cell(0, 5, treatment_group)
    pdf.ln(5)

    pdf.set_font("Poppins", style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 8, "Control Group:", ln=True)
    pdf.set_font("Poppins", size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(
        0,
        5,
        "The control group is used as a baseline for comparison. These are the individuals or units that did not "
        "receive the treatment but were otherwise similar. Here is each location of the control group: ",
    )
    pdf.set_font("Poppins", style="B", size=9.5)
    pdf.multi_cell(0, 5, control_group)
    pdf.ln(5)

    pdf.set_font("Poppins", style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 8, "Minimum Detectable Effect (MDE)", ln=True)
    pdf.set_font("Poppins", size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(
        0,
        5,
        f"The experimental design is based on the minimum detectable effect (MDE) which is the smallest effect "
        f"that can be detected with a given level of confidence. In this case, the MDE is {round(mde * 100)}% "
        f"for the period of {period_idx} days.",
    )
    pdf.ln(5)

    if p_value is not None:
        pdf.set_font("Poppins", style="B", size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Statistical Significance (P-Value)", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        if p_value < 0.001:
            p_value_str = f"{p_value:.6f} (p < 0.001)"
            significance = "Highly Significant"
            explanation = (
                f"The obtained p-value is {p_value_str}, indicating that the result is {significance.lower()}. "
                "This means there is less than a 0.1% chance that these results occurred by chance. "
                "We have extremely strong evidence that the treatment is having a real effect."
            )
        elif p_value < 0.01:
            p_value_str = f"{p_value:.4f} (p < 0.01)"
            significance = "Very Significant"
            explanation = (
                f"The obtained p-value is {p_value_str}, indicating that the result is {significance.lower()}. "
                "This means there is less than a 1% chance that these results occurred by chance. "
                "We have very solid evidence that the treatment is working as expected."
            )
        elif p_value < 0.05:
            p_value_str = f"{p_value:.4f} (p < 0.05)"
            significance = "Significant"
            explanation = (
                f"The obtained p-value is {p_value_str}, indicating that the result is {significance.lower()}. "
                "This means there is less than a 5% chance that these results occurred by chance. "
                "We have good evidence that the treatment is having a positive effect."
            )
        elif p_value < 0.1:
            p_value_str = f"{p_value:.4f} (p < 0.1)"
            significance = "Marginally Significant"
            explanation = (
                f"The obtained p-value is {p_value_str}, indicating that the result is {significance.lower()}. "
                "This means there is less than a 10% chance that these results occurred by chance. "
                "While there is evidence of a treatment effect, the results should be interpreted with some caution."
            )
        else:
            p_value_str = f"{p_value:.4f} (p ≥ 0.1)"
            significance = "Not Significant"
            explanation = (
                f"The obtained p-value is {p_value_str}, indicating that the result is {significance.lower()}. "
                "This means there is more than a 10% chance that these results occurred by chance. "
                "We don't have sufficient evidence to conclude that the treatment is having a real effect."
            )

        pdf.multi_cell(0, 5, explanation)
        pdf.ln(5)

    if power_value is not None:
        pdf.set_font("Poppins", style="B", size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Statistical Power", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        power_percentage = power_value * 100
        if power_percentage >= 80:
            power_interpretation = "High"
            power_explanation = (
                f"The statistical power is {power_percentage:.0f}%, which is considered {power_interpretation.lower()}. "
                "This means we have a high probability of detecting a true effect if one exists. "
                "High power (≥80%) reduces the risk of missing real treatment effects (false negatives)."
            )
        elif power_percentage >= 50:
            power_interpretation = "Moderate"
            power_explanation = (
                f"The statistical power is {power_percentage:.0f}%, which is considered {power_interpretation.lower()}. "
                "This means we have a moderate probability of detecting a true effect if one exists. "
                "While acceptable, higher power would be preferable to reduce the risk of missing real effects."
            )
        else:
            power_interpretation = "Low"
            power_explanation = (
                f"The statistical power is {power_percentage:.0f}%, which is considered {power_interpretation.lower()}. "
                "This means we have a low probability of detecting a true effect if one exists. "
                "Low power increases the risk of missing real treatment effects (false negatives)."
            )

        pdf.multi_cell(0, 5, power_explanation)
        pdf.ln(5)

    # Counterfactual Quality Metrics Section
    if avg_scaled_l2 is not None or smape_value is not None:
        pdf.set_font("Poppins", style="B", size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Counterfactual Quality", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        metrics_text = ""
        if avg_scaled_l2 is not None:
            metrics_text += f"Average Scaled L2 Imbalance: {avg_scaled_l2:.6f}. "
        if smape_value is not None:
            smape_percentage = smape_value if smape_value >= 1 else smape_value * 100
            metrics_text += f"SMAPE: {smape_percentage:.2f}%. "

        pdf.multi_cell(0, 5, metrics_text)
        pdf.ln(2)

        # Quality interpretation based on metrics
        if smape_value is not None:
            smape_percentage = smape_value if smape_value >= 1 else smape_value * 100
            if smape_percentage <= 10:
                quality_level = "excellent"
                quality_explanation = (
                    "These metrics indicate excellent counterfactual quality. The synthetic control model demonstrates "
                    "very high accuracy in replicating the pre-treatment behavior, providing strong confidence "
                    "in the treatment effect estimates."
                )
            elif smape_percentage <= 20:
                quality_level = "good"
                quality_explanation = (
                    "These metrics indicate good counterfactual quality. The synthetic control model shows satisfactory "
                    "accuracy in creating the counterfactual, suggesting reliable experimental design with "
                    "acceptable precision for treatment effect estimation."
                )
            else:
                quality_level = "moderate"
                quality_explanation = (
                    "These metrics indicate moderate counterfactual quality. While the synthetic control provides a "
                    "reasonable approximation, there is some uncertainty in the precision of treatment effect estimates. "
                    "Consider additional model validation."
                )

            pdf.multi_cell(0, 5, quality_explanation)
        pdf.ln(5)

    pdf.set_font("Poppins", style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 8, "Conversion Percentages", ln=True)
    pdf.set_font("Poppins", size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.cell(
        200, 5, f"Treatment Percentage: {(100 - holdout_percentage):.2f}%", ln=True
    )
    pdf.cell(200, 5, f"Holdout Percentage: {holdout_percentage:.2f}%", ln=True)
    pdf.multi_cell(
        0,
        5,
        "The holdout percentage represents the portion of the total conversions that belong to the control group. "
        "The treatment percentage represents the portion of the total conversions that are allocated to the treatment group.",
    )
    pdf.ln(5)

    if pdf.get_y() > 250:
        pdf.add_page()

    pdf.set_font("Poppins", style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 10, "Control Locations and Weights:", ln=True)

    col_width = 95
    row_height = 8
    header_bg = (103, 85, 130)
    alt_row_bg = (209, 204, 217)
    white_row_bg = (246, 246, 246)

    pdf.set_fill_color(*header_bg)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Poppins", style="B", size=10)
    pdf.cell(col_width, row_height, "Location", 1, 0, "C", True)
    pdf.cell(col_width, row_height, "Weight", 1, 1, "C", True)

    pdf.set_text_color(33, 31, 36)
    pdf.set_font("Poppins", size=10)
    for i, row in weights.iterrows():
        bg_color = alt_row_bg if i % 2 else white_row_bg
        pdf.set_fill_color(*bg_color)
        pdf.cell(col_width, row_height, str(row["Control Location"]), 1, 0, "C", True)
        pdf.cell(col_width, row_height, f"{row['Weights']:.4f}", 1, 1, "C", True)

    pdf.ln(5)
    if pdf.get_y() > 250:
        pdf.add_page()

    pdf.set_font("Poppins", style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 10, "Impact", ln=True)
    pdf.set_font("Poppins", size=10)
    pdf.set_text_color(33, 31, 36)

    pdf.multi_cell(
        0,
        5,
        "The results show the impact of the treatment on different treatment locations. "
        "Below is the ATT value and the lift value total of the target variable.",
    )

    pdf.ln(1)
    if pdf.get_y() > 250:
        pdf.add_page()

    pdf.ln(2)
    header_bg = (103, 85, 130)
    row_bg = (246, 246, 246)
    text_color = (33, 31, 36)

    col_widths = [63, 63, 64]
    row_height = 8
    title_height = 10

    pdf.set_fill_color(*header_bg)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Poppins", "B", 12)

    if p_value is not None:
        if p_value < 0.001:
            title_text = f"P-Value: {p_value:.6f} (p < 0.001)"
        elif p_value < 0.01:
            title_text = f"P-Value: {p_value:.4f} (p < 0.01)"
        elif p_value < 0.05:
            title_text = f"P-Value: {p_value:.4f} (p < 0.05)"
        elif p_value < 0.1:
            title_text = f"P-Value: {p_value:.4f} (p < 0.1)"
        else:
            title_text = f"P-Value: {p_value:.4f} (p ≥ 0.1)"
    else:
        title_text = f"Confidence Level {confidence_level * 100}%"

    pdf.cell(190, title_height, title_text, border=1, ln=1, align="C", fill=True)

    pdf.set_text_color(*text_color)
    pdf.set_font("Poppins", "", 10)

    row_data = [
        ("Median Prediction", prediction_value_absolute, prediction_value_percentage),
        ("Lower Bound", lower_bound_value_absolute, lower_bound_value_percentage),
        ("Upper Bound", upper_bound_value_absolute, upper_bound_value_percentage),
    ]

    for i, (label, abs_val, pct_val) in enumerate(row_data):
        bg_color = alt_row_bg if i % 2 else white_row_bg
        pdf.set_fill_color(*bg_color)
        if i == 0:
            pdf.set_font("Poppins", "B", 10)
        else:
            pdf.set_font("Poppins", size=10)
        pdf.cell(col_widths[0], row_height, label, border=1, ln=0, align="C", fill=True)
        pdf.cell(
            col_widths[1],
            row_height,
            f"{abs_val:,.2f}",
            border=1,
            ln=0,
            align="C",
            fill=True,
        )
        pdf.cell(
            col_widths[2],
            row_height,
            f"{pct_val:,.2f}%",
            border=1,
            ln=1,
            align="C",
            fill=True,
        )

    pdf.ln(4)
    pdf.set_font("Poppins", size=11)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(0, 5, f"MDE: {mde * 100}%")
    pdf.ln(5)

    if pdf.get_y() > 250:
        pdf.add_page()

    pdf.set_font("Poppins", size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(
        0,
        5,
        "It is important to be able to identify the impact of the intervention pre-intervention and "
        "post-intervention in real values. In this case, a small table is presented where the pre-intervention "
        "value (with the same duration as the treatment period) and the post-intervention value are observed. "
        "This allows for a quick and simple identification of the impact that an intervention would have in "
        "comparison to the locations where it is not applied (counterfactual).",
    )

    pdf.ln(1)
    if pdf.get_y() > 210:
        pdf.add_page()

    col_widths = [70, 60, 60]
    row_height = 8

    header_texts = [
        "Group",
        f"Pre-treatment\n({firt_report_day} to {second_report_day})",
        f"Post-treatment\n({treatment_day} to {last_day})",
    ]

    max_lines = max(txt.count("\n") + 1 for txt in header_texts)
    max_header_height = max_lines * row_height

    x_start = pdf.get_x()
    y_start = pdf.get_y()

    pdf.set_fill_color(*header_bg)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Poppins", "B", 10)

    x = x_start
    for i, txt in enumerate(header_texts):
        pdf.cell(col_widths[i], max_header_height, "", border=1, ln=0, fill=True)
        current_x = pdf.get_x() - col_widths[i]
        pdf.set_xy(current_x, y_start)

        if "\n" in txt:
            lines = txt.split("\n")
            pdf.cell(col_widths[i], row_height, lines[0], border=0, ln=0, align="C")
            pdf.ln(row_height)
            pdf.set_x(current_x)
            current_font_size = pdf.font_size_pt
            smaller_font = current_font_size * 0.7
            pdf.set_font("Poppins", "B", smaller_font)
            pdf.cell(col_widths[i], row_height, lines[1], border=0, ln=0, align="C")
            pdf.set_font("Poppins", "B", current_font_size)
        else:
            pdf.multi_cell(col_widths[i], row_height, txt, border=0, align="C")

        x += col_widths[i]
        pdf.set_xy(x, y_start)

    pdf.set_xy(x_start, y_start + max_header_height)
    pdf.set_text_color(*text_color)
    pdf.set_font("Poppins", "", 10)

    for i, row in df.iterrows():
        bg_color = alt_row_bg if i % 2 else white_row_bg
        pdf.set_fill_color(*bg_color)
        pdf.cell(
            col_widths[0],
            row_height,
            str(row["Group"]),
            border=1,
            ln=0,
            align="C",
            fill=True,
        )
        pdf.cell(
            col_widths[1],
            row_height,
            f"{row['Pre-treatment']:,.2f}",
            border=1,
            ln=0,
            align="C",
            fill=True,
        )
        pdf.cell(
            col_widths[2],
            row_height,
            f"{row['Post-treatment']:,.2f}",
            border=1,
            ln=1,
            align="C",
            fill=True,
        )

    pdf.ln(9)
    if pdf.get_y() > 170:
        pdf.add_page()
    pdf.set_font("Poppins", size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(
        0,
        5,
        "The graph below shows the aggregate effect, the point effect, and the cumulative effect.",
    )
    pdf.image(temp_image_path, x=10, y=pdf.get_y(), w=190)

    pdf_output = "reporte.pdf"
    pdf.output(pdf_output, "F")
    os.remove(temp_image_path)
    return pdf_output


# Global CSS styling for Streamlit components
st.markdown(
    """
    <style>
    .st-emotion-cache-1652lyb {
        color: black !important;  
    }
    .st-emotion-cache-133trn5 {
        fill: black !important;  
    }
    .st-emotion-cache-8lz9yt {
        fill: black !important;  
    }
    .st-emotion-cache-wifhn2 {
        background-color: #D7D5D7 !important;  
    }
    .st-emotion-cache-1x3ytec {
        background-color: #E1E0E1 !important;  
    }
    div[data-baseweb="select"] > div {
        background-color: #E1E0E1 !important;  
    }
    input, textarea {
        background-color: #E1E0E1 !important; 
    }
    
    </style>
    """,
    unsafe_allow_html=True,
)

# Main app interface starts here
st.title("Experimental Design")

# Initialize all session state variables for app workflow
if "results" not in st.session_state:
    st.session_state.results = None
if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = None
if "sensitivity_results" not in st.session_state:
    st.session_state.sensitivity_results = None
if "graph_generated" not in st.session_state:
    st.session_state.graph_generated = False
if "current_fig" not in st.session_state:
    st.session_state.current_fig = None
if "simulation_button_clicked" not in st.session_state:
    st.session_state.simulation_button_clicked = False
if "simulation_running" not in st.session_state:
    st.session_state.simulation_running = False
if "selected_point" not in st.session_state:
    st.session_state.selected_point = None
if "last_params" not in st.session_state:
    st.session_state.last_params = {}
if "fig2" not in st.session_state:
    st.session_state.fig2 = None
# STEP 1: File upload and data validation
st.subheader("1. Upload file")


# Table styling helper function
def style_table(df):
    return (
        df.style.set_table_styles(
            [
                {
                    "selector": "thead th",
                    "props": [
                        ("font-weight", "bold"),
                        ("color", "black"),
                        ("background-color", "#f0f0f0"),
                        ("font-size", "16px"),
                        ("text-align", "center"),
                    ],
                }
            ]
        )
        .set_properties(**{"text-align": "center", "white-space": "nowrap"})
        .set_table_attributes('class="dataframe"')
    )


# File uploader for CSV data
file = st.file_uploader("Choose a file ", type=["csv"])

# Main workflow when file is uploaded
if file is not None:
    data = pd.read_csv(file)

    if data is not None:
        st.markdown(
            """
            <style>
            .dataframe-container {
                width: 100%;
                overflow-x: auto;
            }
            .dataframe-container table {
                width: 100%;
                border-collapse: collapse;
            }
            </style>
        """,
            unsafe_allow_html=True,
        )

        styled_table = style_table(data.head()).to_html()

        st.markdown(
            f'<div class="dataframe-container">{styled_table}</div>',
            unsafe_allow_html=True,
        )

        # Column mapping interface for dates, locations, and target variable
        st.text("Type the name of columns for the following parameters:")
        col1, col2, col3 = st.columns(3)

        def normalize_text(text):
            """Remove accents and convert to lowercase"""
            if not isinstance(text, str):
                return str(text).lower()
            return "".join(
                c
                for c in unicodedata.normalize("NFD", text)
                if unicodedata.category(c) != "Mn"
            ).lower()

        def reset_states():
            st.session_state.graph_generated = False
            st.session_state.current_fig = None
            st.session_state.simulation_button_clicked = False

        # Auto-detect column types using keywords
        contains_date = ["date", "day", "time", "fecha", "dia", "tiempo"]
        contains_locations = [
            "location",
            "region",
            "state",
            "ubicacion",
            "region",
            "estado",
        ]
        contains_date_norm = [normalize_text(x) for x in contains_date]
        contains_locations_norm = [normalize_text(x) for x in contains_locations]

        with col1:
            matching_column1 = next(
                (
                    col
                    for col in data.columns
                    if any(p in normalize_text(col) for p in contains_date_norm)
                ),
                None,
            )
            col_dates = st.text_input(
                "Date",
                matching_column1 if matching_column1 else "",
                on_change=reset_states,
                key="dates",
            )
        with col2:
            matching_column2 = next(
                (
                    col
                    for col in data.columns
                    if any(q in normalize_text(col) for q in contains_locations_norm)
                ),
                None,
            )
            if matching_column2:
                data[matching_column2] = data[matching_column2].astype(str)
            col_locations = st.text_input(
                "Locations",
                matching_column2 if matching_column2 else "",
                on_change=reset_states,
                key="locations",
            )

        with col3:
            target_columns = [
                col
                for col in data.columns
                if not any(d in normalize_text(col) for d in contains_date_norm)
                and not any(l in normalize_text(col) for l in contains_locations_norm)
            ]
            col_target = st.selectbox(
                "Target", target_columns, on_change=reset_states, key="target"
            )

        if col_dates == "" or col_locations == "" or col_target == "":
            st.warning(
                "Please fill in all required fields (Dates, Locations, and Target)."
            )
        elif (
            col_dates not in data.columns
            or col_locations not in data.columns
            or col_target not in data.columns
        ):
            st.error("Please enter correct column names.")
            st.stop()
        else:
            if "graph_generated" not in st.session_state:
                st.session_state.graph_generated = False
            if "current_fig" not in st.session_state:
                st.session_state.current_fig = None
            if col_dates and col_locations and col_target:
                try:
                    if col_locations in data.columns:
                        data[col_locations] = data[col_locations].astype(str)
                    cleaned = cleaned_data(
                        data,
                        col_target=col_target,
                        col_locations=col_locations,
                        col_dates=col_dates,
                    )
                except TypeError as e:
                    st.error(str(e))
                    st.stop()
                except ValueError as e:
                    st.error(str(e))
                    st.stop()
                except Exception as e:
                    st.error(str(e))
                    st.stop()
            # STEP 2: Data visualization
            st.subheader("2. Data visualization")
            if "graph_button_clicked" not in st.session_state:
                st.session_state.graph_button_clicked = False

            # Generate geographic data visualization
            if st.button("Graph data"):
                st.session_state.graph_button_clicked = True

            if st.session_state.graph_button_clicked:
                fig = plot_geodata(cleaned)
                st.session_state.fig = fig
                st.markdown(
                    """
                    <style>
                    .js-plotly-plot .plotly .cursor-crosshair {
                         cursor: default !important;
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    st.session_state.fig,
                    config={
                        "modeBarButtonsToRemove": [
                            "zoom2d",
                            "pan2d",
                            "select2d",
                            "lasso2d",
                            "resetScale2d",
                        ],
                        "displaylogo": False,
                    },
                )
            # STEP 3: Experimental design configuration
            st.subheader("3. Experimental design")
            st.text("Parameter configuration")

            st.markdown(
                """
            <style>
                .stMultiSelect span[data-baseweb="tag"] {
                    background-color: #ecf2f7 !important;
                    color: black !important;
                }

            """,
                unsafe_allow_html=True,
            )
            # Location exclusion and test type selection
            excluded_locations = st.multiselect(
                "Select excluded locations", cleaned["location"].unique()
            )

            # Analyze data and recommend statistical test
            data_analysis = analyze_data_characteristics(cleaned, col_target="Y")

            recommended_test = data_analysis.get("recommended_test", "sum")

            test_options = {
                "sum": "Sum Test - Total cumulative effect",
                "mean_diff": "Mean Difference Test - Average effect",
                "t_test": "T-Test - Standardized mean difference",
                "median_diff": "Median Difference Test - Robust to outliers",
            }

            selected_test = recommended_test

            st.markdown(
                """
                <style>
                    div[role="slider"] {
                        background-color: #3e7cb1 !important;
                    }
                    
                    div[data-testid="stSliderTickBarMin"] {
                        color: black !important;
                        background-color:: red !important;
                    }

                    div[data-testid="stSliderTickBarMax"] {
                        color: black !important;
                    }
                    
                    div[data-testid="stSliderThumbValue"] {
                        color: #3e7cb1 !important;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )

            # Treatment percentage configuration
            maximum_treatment_percentage_pre = st.slider(
                "Select maximum treatment percentage (%)",
                5,
                50,
                30,
                help="Maximum percentage of the target variable that can be contained in the treatment group",
            )
            maximum_treatment_percentage = maximum_treatment_percentage_pre / 100

            # Statistical significance configuration
            significance_level_pre = st.number_input(
                "Select significance level (%)",
                min_value=1,
                max_value=100,
                value=5,
                step=1,
                help="Threshold to judge a result as statistically significant. For example, with a 10% significance level, it means you have a 90% confidence level",
            )
            significance_level = significance_level_pre / 100
            if significance_level > 0.20:
                st.warning("A high value could lead to false results")
            # Lift range configuration (effect size)
            st.text("Select range of lifts")
            col1, col2, col3 = st.columns(3)
            with col1:
                delta_min = st.number_input(
                    "Lift Min:", min_value=0.00, max_value=0.9, value=0.01, step=0.01
                )
            with col2:
                delta_max = st.number_input(
                    "Lift Max:", min_value=0.02, max_value=1.0, value=0.15, step=0.01
                )
            with col3:
                delta_step = st.number_input(
                    "Lift Step:", min_value=0.00, max_value=1.0, value=0.01, step=0.01
                )
            if delta_min > delta_max:
                st.error("Lift Min must be less than Lift Max")
                st.stop()
            elif delta_min == delta_max:
                st.error("Lift Min and Lift Max must be different")
                st.stop()
            elif delta_step == delta_max:
                st.error("Lift Step must be less than Lift Max")
                st.stop()
            elif delta_step > delta_max - delta_min:
                st.error("Lift Step must be less than the range of lifts")
                st.stop()
            else:
                deltas_range = (delta_min, delta_max, delta_step)
            # Period range configuration (experiment duration)
            st.text("Select range of periods")
            col1, col2, col3 = st.columns(3)
            with col3:
                period_step = st.number_input(
                    "Period Step:", min_value=1, max_value=100, value=5, step=1
                )
            with col1:
                period_min = st.number_input(
                    "Period Min:", min_value=1, max_value=100, value=5, step=period_step
                )
            with col2:
                period_max = st.number_input(
                    "Period Max:",
                    min_value=5,
                    max_value=100,
                    value=30,
                    step=period_step,
                )

            if period_min > period_max:
                st.error("Period Min must be less than Period Max")
                st.stop()
            elif period_min == period_max:
                st.error("Period Min and Period Max must be different")
                st.stop()
            elif period_step == period_max:
                st.error("Period Step must be less than Period Max")
                st.stop()
            elif period_step > period_max - period_min:
                st.error("Period Step must be less than the range of periods")
                st.stop()
            else:
                periods_range = (period_min, period_max + 1, period_step)

            # Multi-cell mode toggle for advanced analysis
            enable_multicell = st.checkbox(
                "Enable Multi-Cell Mode",
                value=False,
                help="Enable to create a single optimized experiment with multiple cells of different sizes",
                key="multicell_checkbox",
            )

            # Multi-cell configuration
            multicell_config = None
            if enable_multicell:
                col1, col2 = st.columns(2)
                with col1:
                    unique_locations = cleaned["location"].unique()
                    no_locations = len(unique_locations)
                    max_group_size = round(no_locations * 0.45)
                    min_elements_in_treatment = round(no_locations * 0.05)

                    available_sizes = list(
                        range(min_elements_in_treatment, max_group_size + 1)
                    )
                    selected_sizes = st.multiselect(
                        "Allowed Group Sizes",
                        options=available_sizes,
                        default=(
                            available_sizes[:3]
                            if len(available_sizes) >= 3
                            else available_sizes
                        ),
                        help="Choose the pool of allowed sizes for cells in the experiment. The system will select the best combination.",
                        key="multicell_sizes",
                    )

                with col2:
                    top_n_per_size = st.number_input(
                        "Total Number of Cells",
                        min_value=1,
                        max_value=10,
                        value=3,
                        help="Total number of cells in the final experiment (may have different sizes)",
                        key="multicell_top_n",
                    )

                if selected_sizes:
                    multicell_config = {
                        "sizes": selected_sizes,
                        "top_n": top_n_per_size,
                    }

            if "simulation_results" not in st.session_state:
                st.session_state.simulation_results = None
                st.session_state.sensitivity_results = None
                st.session_state.results = None

            if "selected_point" not in st.session_state:
                st.session_state.selected_point = None

            if "last_params" not in st.session_state:
                st.session_state.last_params = {}

            # Track parameter changes to reset simulation state
            current_params = {
                "excluded_locations": excluded_locations,
                "maximum_treatment_percentage_pre": maximum_treatment_percentage_pre,
                "significance_level_pre": significance_level_pre,
                "deltas_range": (delta_min, delta_max, delta_step),
                "periods_range": (period_min, period_max + 1, period_step),
                "col_target": col_target,
                "enable_multicell": enable_multicell,
                "multicell_config": multicell_config,
            }

            # Reset simulation state when parameters change
            if current_params != st.session_state.last_params:
                if st.session_state.simulation_running:
                    app_logger.info("🚫 CANCELLING SIMULATION: Parameters changed during execution")
                st.session_state.simulation_button_clicked = False
                st.session_state.simulation_running = False  # Cancel any running simulation
                st.session_state.selected_point = None
                st.session_state.simulation_results = None
                st.session_state.sensitivity_results = None
                st.session_state.results = None
                st.session_state.fig2 = None
                st.session_state.last_params = current_params

            if "simulation_button_clicked" not in st.session_state:
                st.session_state.simulation_button_clicked = False

            if st.session_state.simulation_running:
                st.warning("⏳ Simulation in progress... Please wait or update parameters to cancel.")
            elif st.session_state.simulation_button_clicked:
                st.info("💡 Simulation completed! To run again, update any parameter above.")
            else:
                st.text("Click on the button to start simulation")

            # Simulation execution control
            run_simulation = False
            if not st.session_state.simulation_button_clicked and not st.session_state.simulation_running:
                run_simulation = st.button(
                    "Run Simulation", 
                    help="Start the simulation with current parameters",
                    key="run_simulation_btn"
                )
            else:
                st.empty()

            if run_simulation:
                st.session_state.simulation_button_clicked = True
                st.session_state.simulation_running = True
                st.rerun()

            # Execute simulation with configured parameters
            if st.session_state.simulation_running and st.session_state.simulation_button_clicked and not run_simulation:
                try:
                    with st.spinner("Running simulation..."):
                        if not st.session_state.simulation_running:
                            st.info("Simulation was cancelled due to parameter changes.")
                            st.stop()
                            
                        st.session_state.is_multicell_mode = False

                        # Run main geo analysis simulation
                        results = run_geo_analysis_streamlit_app(
                            data=cleaned,
                            excluded_locations=excluded_locations,
                            maximum_treatment_percentage=maximum_treatment_percentage,
                            significance_level=significance_level,
                            deltas_range=deltas_range,
                            periods_range=periods_range,
                            multicell_config=multicell_config,
                            test_type=selected_test,
                            inference_type="iid",
                            global_optimization=enable_multicell,
                        )

                    if results is None:
                        st.error("❌ Analysis failed. The algorithm could not find valid treatment/control groups with the current settings.")
                        
                        # Check data quality first
                        if cleaned["Y"].sum() == 0:
                            st.error("🔍 **Root Cause**: Your data has no positive values in the target variable 'Y'")
                            st.info("📊 **Data Requirements**: Ensure your data contains non-zero values in the 'Y' column")
                        else:
                            st.info("💡 **Possible Solutions:**")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("""
                                **Configuration Adjustments:**
                                - **Reduce Maximum Treatment Percentage** (try 20-30%)
                                - **Exclude fewer locations** from the analysis
                                - **Try different group sizes** (if using multi-cell mode)
                                """)
                            with col2:
                                st.markdown("""
                                **Data Quality Checks:**
                                - Ensure sufficient time periods (≥30 periods recommended)
                                - Check for adequate location diversity (≥8 locations)
                                - Verify Y values are positive and meaningful
                                """)
                        
                        # Show current settings for debugging
                        with st.expander("🔧 Current Analysis Settings", expanded=False):
                            st.write(f"**Maximum Treatment Percentage:** {maximum_treatment_percentage*100:.1f}%")
                            st.write(f"**Excluded Locations:** {len(excluded_locations)} locations")
                            st.write(f"**Total Locations Available:** {len(cleaned['location'].unique())} locations")
                            st.write(f"**Time Periods:** {len(cleaned['time'].unique())} periods")
                            st.write(f"**Total Y Sum:** {cleaned['Y'].sum():,.2f}")
                            if enable_multicell and multicell_config:
                                st.write(f"**Multi-cell Sizes:** {multicell_config['sizes']}")
                                st.write(f"**Number of Cells:** {multicell_config['top_n']}")
                        st.stop()

                    results_by_size = transform_results_data(
                        results["simulation_results"]
                    )

                    st.session_state.results = results
                    st.session_state.simulation_results = results_by_size
                    st.session_state.sensitivity_results = results[
                        "sensitivity_results"
                    ]
                    st.session_state.full_results = results
                    st.session_state.multicell_config = (
                        multicell_config if enable_multicell else None
                    )
                    periods = list(np.arange(*periods_range))

                    # Determine visualization mode and generate plots
                    if (
                        enable_multicell
                        and multicell_config
                        and st.session_state.results.get("simulation_results")
                    ):
                        st.session_state.is_multicell_mode = True
                    else:
                        st.session_state.is_multicell_mode = False
                    # Skip heatmap generation for multicell mode
                    if st.session_state.is_multicell_mode:
                        st.session_state.fig2 = None
                        st.info("📊 Multicell mode: Heatmap visualization not applicable for global optimization results.")
                    else:
                        try:
                            st.session_state.fig2 = plot_mde_results(
                                results_by_size, results["sensitivity_results"], periods
                            )
                        except ValueError as e:
                            st.error(f"Error generating the heatmap: {e}")
                            st.session_state.simulation_running = False
                            st.stop()
                        
                    st.session_state.simulation_running = False
                    app_logger.info("✅ SIMULATION COMPLETED: Analysis finished successfully")
                    st.success("✅ Simulation completed successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.session_state.simulation_running = False
                    st.error(f"Simulation failed: {str(e)}")
                    st.exception(e)
                    st.rerun()

            # STEP 4: Display results based on mode (single-cell vs multi-cell)
            if st.session_state.simulation_button_clicked and st.session_state.results:
                if (
                    enable_multicell
                    and multicell_config
                    and getattr(st.session_state, "is_multicell_mode", False)
                    and st.session_state.results
                    and st.session_state.results.get("simulation_results")
                ):
                    st.write(" ")
                    st.subheader("Global Multi-Cell Experiment Results")

                    simulation_results = st.session_state.results["simulation_results"]

                    # Check if we have global experiment results
                    if "global_experiment" in simulation_results:
                        global_experiment = simulation_results["global_experiment"]

                        # Get sensitivity data for MDE/Power information
                        sensitivity_data = st.session_state.results.get(
                            "sensitivity_results", {}
                        )
                        
                        # Handle case where sensitivity_results is None (multicell mode)
                        if sensitivity_data is None:
                            sensitivity_data = {}

                        # Period selection for MDE display
                        available_periods = set()
                        for size_data in sensitivity_data.values():
                            if isinstance(size_data, dict):
                                available_periods.update(size_data.keys())
                        available_periods = sorted(list(available_periods))

                        selected_period = None
                        if available_periods:
                            selected_period = st.selectbox(
                                "Select Period for MDE/Power Display",
                                options=available_periods,
                                index=0,
                                help="Choose the treatment period to display MDE, P-Value, and Power statistics"
                            )
                        else:
                            st.warning(
                                "No sensitivity data available for period selection."
                            )

                    # Build detailed results table for multi-cell mode
                    detailed_results = []

                    for size, data in st.session_state.results[
                        "simulation_results"
                    ].items():
                        if isinstance(data, list):
                            for idx, group in enumerate(data):

                                mde_info = {}
                                if (
                                    size in sensitivity_data
                                    and selected_period is not None
                                ):
                                    period_data = sensitivity_data[size].get(
                                        selected_period, {}
                                    )
                                    mde_raw = period_data.get("MDE")
                                    mde_value = (
                                        mde_raw * 100 if mde_raw is not None else None
                                    )
                                    p_value = period_data.get("P-Value")
                                    power_raw = period_data.get("Power")
                                    power_value = (
                                        power_raw * 100
                                        if power_raw is not None
                                        else None
                                    )

                                    mde_info = {
                                        "MDE": (
                                            f"{int(round(mde_value))}"
                                            if mde_value is not None
                                            else "N/A"
                                        ),
                                        "Period": selected_period,
                                        "P-Value": (
                                            f"{p_value:.4f}"
                                            if p_value is not None
                                            else "N/A"
                                        ),
                                        "Power": (
                                            f"{int(round(power_value))}"
                                            if power_value is not None
                                            else "N/A"
                                        ),
                                    }
                                else:
                                    mde_info = {
                                        "MDE": "N/A",
                                        "Period": "N/A",
                                        "P-Value": "N/A",
                                        "Power": "N/A",
                                    }

                                detailed_results.append(
                                    {
                                        "Size": size,
                                        "Rank": idx + 1,
                                        "Treatment Group": ", ".join(
                                            group["Best Treatment Group"]
                                        ),
                                        "Control Group": ", ".join(
                                            group["Control Group"]
                                        ),
                                        "SMAPE": f"{group['SMAPE']:.4f}",
                                        "Holdout %": f"{group['Holdout Percentage']:.2f}%",
                                        "MDE": f"{mde_info['MDE']}%",
                                        "Period": mde_info["Period"],
                                        "P-Value": mde_info["P-Value"],
                                        "Power": f"{mde_info['Power']}%",
                                    }
                                )

                    if detailed_results:
                        df_detailed = pd.DataFrame(detailed_results)

                        df_detailed = df_detailed.sort_values(["Size", "Rank"])

                        # Format results for display
                        detailed_results = []

                        for cell in global_experiment:
                            cell_size = cell["Size"]

                            # Get MDE info for this cell size and period
                            mde_info = {"MDE": "N/A", "P-Value": "N/A", "Power": "N/A"}
                            if selected_period and sensitivity_data:
                                # Check if cell_size exists in sensitivity_data
                                if cell_size in sensitivity_data:
                                    size_data = sensitivity_data[cell_size]
                                    if (
                                        isinstance(size_data, dict)
                                        and selected_period in size_data
                                    ):
                                        period_data = size_data[selected_period]
                                        mde_raw = period_data.get("MDE")
                                        mde_value = (
                                            mde_raw * 100
                                            if mde_raw is not None
                                            else None
                                        )
                                        p_value = period_data.get("P-Value")
                                        power_raw = period_data.get("Power")
                                        power_value = (
                                            power_raw * 100
                                            if power_raw is not None
                                            else None
                                        )

                                        mde_info = {
                                            "MDE": (
                                                f"{int(round(mde_value))}"
                                                if mde_value is not None
                                                else "N/A"
                                            ),
                                            "P-Value": (
                                                f"{p_value:.4f}"
                                                if p_value is not None
                                                else "N/A"
                                            ),
                                            "Power": (
                                                f"{int(round(power_value))}"
                                                if power_value is not None
                                                else "N/A"
                                            ),
                                        }
                                else:
                                    # If exact size not found, try to find closest size
                                    available_sizes = [
                                        int(s)
                                        for s in sensitivity_data.keys()
                                        if str(s).isdigit()
                                    ]
                                    if available_sizes:
                                        closest_size = min(
                                            available_sizes,
                                            key=lambda x: abs(x - cell_size),
                                        )
                                        size_data = sensitivity_data[closest_size]
                                        if (
                                            isinstance(size_data, dict)
                                            and selected_period in size_data
                                        ):
                                            period_data = size_data[selected_period]
                                            mde_raw = period_data.get("MDE")
                                            mde_value = (
                                                mde_raw * 100
                                                if mde_raw is not None
                                                else None
                                            )
                                            p_value = period_data.get("P-Value")
                                            power_raw = period_data.get("Power")
                                            power_value = (
                                                power_raw * 100
                                                if power_raw is not None
                                                else None
                                            )

                                            mde_info = {
                                                "MDE": (
                                                    f"{int(round(mde_value))}"
                                                    if mde_value is not None
                                                    else f"N/A (≈{closest_size})"
                                                ),
                                                "P-Value": (
                                                    f"{p_value:.4f}"
                                                    if p_value is not None
                                                    else "N/A"
                                                ),
                                                "Power": (
                                                    f"{int(round(power_value))}"
                                                    if power_value is not None
                                                    else f"N/A (≈{closest_size})"
                                                ),
                                            }

                            detailed_results.append(
                                {
                                    "Cell": cell["Cell"],
                                    "Size": cell["Size"],
                                    "Treatment Group": ", ".join(
                                        cell["Best Treatment Group"]
                                    ),
                                    "Control Group": ", ".join(cell["Control Group"]),
                                    "SMAPE": f"{cell['SMAPE']:.4f}",
                                    "Holdout %": f"{cell['Holdout Percentage']:.2f}%",
                                    "MDE": (
                                        f"{mde_info['MDE']}%"
                                        if mde_info["MDE"] != "N/A"
                                        else "N/A"
                                    ),
                                    "P-Value": mde_info["P-Value"],
                                    "Power": (
                                        f"{mde_info['Power']}%"
                                        if mde_info["Power"] != "N/A"
                                        else "N/A"
                                    ),
                                }
                            )

                        if detailed_results:
                            df_detailed = pd.DataFrame(detailed_results)
                            df_detailed = df_detailed.sort_values("Cell")


                            st.dataframe(
                                df_detailed,
                                use_container_width=True,
                                height=min(600, len(detailed_results) * 35 + 50),
                            )

                            # Download button
                            csv = df_detailed.to_csv(index=False)
                            st.download_button(
                                label="Download Global Experiment Results as CSV",
                                data=csv,
                                file_name=f"global_multicell_experiment_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                            )

                            # Show location usage summary
                            all_treatment_locations = set()
                            all_control_locations = set()
                            for cell in global_experiment:
                                all_treatment_locations.update(
                                    cell["Best Treatment Group"]
                                )
                                all_control_locations.update(cell["Control Group"])

                            total_unique_locations = len(
                                all_treatment_locations | all_control_locations
                            )

                            with st.expander(
                                "📍 Location Usage Summary", expanded=False
                            ):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric(
                                        "Treatment Locations",
                                        len(all_treatment_locations),
                                    )
                                with col2:
                                    st.metric(
                                        "Control Locations", len(all_control_locations)
                                    )
                                with col3:
                                    st.metric(
                                        "Total Unique Locations", total_unique_locations
                                    )

                                st.write(
                                    "**Treatment Locations Used:**",
                                    ", ".join(sorted(all_treatment_locations)),
                                )
                                st.write(
                                    "**Control Locations Used:**",
                                    ", ".join(sorted(all_control_locations)),
                                )

                        else:
                            st.warning("No experiment results to display.")

                    # Handle legacy multi-cell results (if any)
                    else:
                        st.warning(
                            "⚠️ Legacy multi-cell mode detected. Please re-run the simulation to use the new global optimization."
                        )

                # Single-cell mode: interactive heatmap and point selection
                elif st.session_state.simulation_results is not None and not getattr(
                    st.session_state, "is_multicell_mode", False
                ):

                    st.markdown(
                        """
                        <style>
                        .js-plotly-plot .plotly .cursor-move {
                            cursor: default !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.write(
                        '<h4 style="text-align: center;"> Geo Murray MDE Heatmap</h4>',
                        unsafe_allow_html=True,
                    )
                    fig2 = st.session_state.fig2
                    if fig2 is None or not hasattr(fig2, "to_dict"):
                        st.error("Heatmap could not be generated for these parameters.")
                        event = st.empty()
                    else:
                        event = st.plotly_chart(
                            fig2,
                            key="heatmap",
                            on_select="rerun",
                            config={
                                "modeBarButtonsToRemove": [
                                    "zoom2d",
                                    "pan2d",
                                    "select2d",
                                    "lasso2d",
                                    "resetScale2d",
                                ],
                                "displaylogo": False,
                            },
                        )

                    # Handle heatmap point selection
                    selected_point = None
                    if hasattr(event, 'selection') and event.selection is not None:
                        selected_point = event.selection

                    if (
                        selected_point
                        and isinstance(selected_point, dict)
                        and "points" in selected_point
                        and len(selected_point["points"]) > 0
                    ):
                        point = selected_point["points"][0]
                        if "x" in point and "y" in point:
                            st.session_state.selected_point = point

                    # Display detailed info for selected point
                    if st.session_state.selected_point:
                        x_value, y_value = (
                            st.session_state.selected_point["x"],
                            st.session_state.selected_point["y"],
                        )
                        treatment_percentage = round(100 - float(y_value.strip("%")), 2)
                        try:
                            if isinstance(x_value, str) and "Day-" in x_value:
                                period_idx = int(x_value.replace("Day-", ""))
                            else:
                                period_idx = None

                            if isinstance(y_value, (int, float)):
                                y_value_str = f"{treatment_percentage:.2f}%"

                            else:
                                y_value_str = str(f"{treatment_percentage}%")

                            st.write(
                                f"###### Locations with a treatment percentage of: {y_value_str}"
                            )

                            location = None
                            for (
                                loc,
                                data,
                            ) in st.session_state.simulation_results.items():

                                holdout_str = f"{data['Holdout Percentage']:.2f}%"
                                if holdout_str == y_value:
                                    location = loc
                                    break

                            if location is None:
                                st.write(
                                    f"Error: Location not found for the holdout percentage: {y_value_str}"
                                )
                            else:
                                treatment_group = (
                                    st.session_state.simulation_results.get(
                                        location, {}
                                    ).get("Best Treatment Group", "N/A")
                                )
                                control_group = st.session_state.simulation_results.get(
                                    location, {}
                                ).get("Control Group", "N/A")
                                st.write(f"- **Treatment group:** {treatment_group}")
                                st.write(f"- **Control group:** {control_group}")

                                mde = "N/A"
                                if period_idx is not None and y_value is not None:
                                    y_value_float = (
                                        float(y_value.strip("%"))
                                        if isinstance(y_value, str)
                                        else float(y_value)
                                    )
                                    matching_size = None
                                    for (
                                        size,
                                        data,
                                    ) in st.session_state.simulation_results.items():
                                        if (
                                            abs(
                                                float(data["Holdout Percentage"])
                                                - y_value_float
                                            )
                                            < 0.01
                                        ):
                                            matching_size = size
                                            break

                                    mde = None
                                    power = None
                                    if matching_size is not None and st.session_state.sensitivity_results is not None:
                                        mde = st.session_state.sensitivity_results[
                                            matching_size
                                        ][period_idx]["MDE"]
                                        power = st.session_state.sensitivity_results[
                                            matching_size
                                        ][period_idx].get("Power", None)

                                if mde is not None:
                                    st.write(
                                        f"- **Minimum Detectable Effect (MDE):** {round(mde*100)}%"
                                    )
                                if power is not None:
                                    st.write(
                                        f"- **Statistical Power:** {round(power*100)}%"
                                    )

                                # Display error metrics
                                if matching_size is not None:
                                    avg_scaled_l2 = st.session_state.simulation_results[matching_size].get("AvgScaledL2Imbalance", None)
                                    smape_val = st.session_state.simulation_results[matching_size].get("SMAPE", None)

                                    if avg_scaled_l2 is not None:
                                        st.write(f"- **AvgScaledL2Imbalance:** {avg_scaled_l2:.6f}")
                                    if smape_val is not None:
                                        st.write(f"- **SMAPE:** {round(smape_val, 2)}%")

                                random_sate = cleaned["location"].unique()[0]
                                filtered_data = cleaned[
                                    cleaned["location"] == random_sate
                                ]
                                firt_day = filtered_data["time"].min()
                                last_day = filtered_data["time"].max()
                                second_report_day = last_day - pd.Timedelta(
                                    days=period_idx
                                )
                                firt_report_day = last_day - pd.Timedelta(
                                    days=(period_idx * 2) - 1
                                )
                                treatment_day = last_day - pd.Timedelta(
                                    days=period_idx - 1
                                )
                                last_day = last_day.strftime("%Y-%m-%d")
                                firt_day = firt_day.strftime("%Y-%m-%d")
                                firt_report_day = firt_report_day.strftime("%Y-%m-%d")
                                second_report_day = second_report_day.strftime(
                                    "%Y-%m-%d"
                                )
                                treatment_day = treatment_day.strftime("%Y-%m-%d")
                                holdout_percentage = (
                                    st.session_state.simulation_results[location][
                                        "Holdout Percentage"
                                    ]
                                )
                                treatment_states = treatment_group.split(",")
                                length_treatment = len(treatment_states)

                                # STEP 5: PDF report generation
                                st.subheader("4. Generate report of results")
                                st.write(
                                    "Click on the button to generate and download the PDF report."
                                )
                                # Generate comprehensive PDF report
                                if st.button("Generate and Download PDF"):
                                    with st.spinner("Generating report..."):
                                        if (
                                            "selected_point" in st.session_state
                                            and st.session_state.selected_point
                                        ):
                                            point = st.session_state.selected_point
                                            y_value = point["y"]
                                            y_value_str = (
                                                f"{y_value:.2f}%"
                                                if isinstance(y_value, (int, float))
                                                else str(y_value)
                                            )

                                            if st.session_state.results is None:
                                                st.error(
                                                    "Please run the simulation first before generating a PDF."
                                                )
                                                st.stop()

                                            location = None
                                            for (
                                                loc,
                                                data,
                                            ) in (
                                                st.session_state.simulation_results.items()
                                            ):
                                                holdout_str = (
                                                    f"{data['Holdout Percentage']:.2f}%"
                                                )
                                                if holdout_str == y_value_str:
                                                    location = loc
                                                    break

                                            if location is None:
                                                st.write(
                                                    f"Location not found for the holdout percentage: {y_value_str}"
                                                )
                                            else:
                                                treatment_group = (
                                                    st.session_state.simulation_results[
                                                        location
                                                    ]["Best Treatment Group"]
                                                )
                                                control_group = (
                                                    st.session_state.simulation_results[
                                                        location
                                                    ]["Control Group"]
                                                )
                                                # Generate impact analysis plots and data
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
                                                    st.session_state.results,
                                                    period_idx,
                                                    holdout_percentage,
                                                    length_treatment,
                                                    significance_level,
                                                )
                                                prediction_value_absolute = (
                                                    prediction_value
                                                )
                                                prediction_value_percentage = (
                                                    (
                                                        prediction_value
                                                        - np.sum(post_counterfactual)
                                                    )
                                                    / np.abs(
                                                        np.sum(post_counterfactual)
                                                    )
                                                    * 100
                                                )
                                                lower_bound_value_absolute = (
                                                    lower_bound_value
                                                )
                                                lower_bound_value_percentage = (
                                                    (
                                                        lower_bound_value
                                                        - np.sum(post_counterfactual)
                                                    )
                                                    / np.abs(
                                                        np.sum(post_counterfactual)
                                                    )
                                                    * 100
                                                )
                                                upper_bound_value_absolute = (
                                                    upper_bound_value
                                                )
                                                upper_bound_value_percentage = (
                                                    (
                                                        upper_bound_value
                                                        - np.sum(post_counterfactual)
                                                    )
                                                    / np.abs(
                                                        np.sum(post_counterfactual)
                                                    )
                                                    * 100
                                                )
                                                weights = print_weights(
                                                    st.session_state.results,
                                                    treatment_percentage,
                                                )
                                                confidence_level = (
                                                    1 - significance_level
                                                )

                                                p_value = None
                                                power_value = None
                                                if (
                                                    matching_size is not None
                                                    and period_idx is not None
                                                    and st.session_state.sensitivity_results is not None
                                                ):
                                                    if (
                                                        matching_size
                                                        in st.session_state.sensitivity_results
                                                    ):
                                                        if (
                                                            period_idx
                                                            in st.session_state.sensitivity_results[
                                                                matching_size
                                                            ]
                                                        ):
                                                            p_value = st.session_state.sensitivity_results[
                                                                matching_size
                                                            ][
                                                                period_idx
                                                            ].get(
                                                                "P-Value", None
                                                            )
                                                            power_value = st.session_state.sensitivity_results[
                                                                matching_size
                                                            ][
                                                                period_idx
                                                            ].get(
                                                                "Power", None
                                                            )

                                                # Get error metrics
                                                avg_scaled_l2_val = None
                                                smape_val = None
                                                if matching_size is not None and st.session_state.simulation_results is not None:
                                                    avg_scaled_l2_val = st.session_state.simulation_results[matching_size].get("AvgScaledL2Imbalance", None)
                                                    smape_val = st.session_state.simulation_results[matching_size].get("SMAPE", None)

                                                df = pd.DataFrame(
                                                    {
                                                        "Group": [
                                                            "Treatment",
                                                            "Counterfactual (control)",
                                                            "Absolute difference",
                                                        ],
                                                        "Pre-treatment": [
                                                            np.sum(pre_treatment),
                                                            np.sum(pre_counterfactual),
                                                            np.abs(
                                                                np.sum(pre_treatment)
                                                                - np.sum(
                                                                    pre_counterfactual
                                                                )
                                                            ),
                                                        ],
                                                        "Post-treatment": [
                                                            np.sum(post_treatment),
                                                            np.sum(post_counterfactual),
                                                            np.abs(
                                                                np.sum(post_treatment)
                                                                - np.sum(
                                                                    post_counterfactual
                                                                )
                                                            ),
                                                        ],
                                                    }
                                                )

                                                # Create PDF with all experimental results
                                                pdf_file = generate_pdf(
                                                    treatment_group,
                                                    control_group,
                                                    holdout_percentage,
                                                    impact_graph,
                                                    weights,
                                                    period_idx,
                                                    mde,
                                                    att,
                                                    incremental,
                                                    col_target,
                                                    firt_day,
                                                    last_day,
                                                    treatment_day,
                                                    df,
                                                    firt_report_day,
                                                    second_report_day,
                                                    prediction_value_absolute,
                                                    prediction_value_percentage,
                                                    lower_bound_value_absolute,
                                                    lower_bound_value_percentage,
                                                    upper_bound_value_absolute,
                                                    upper_bound_value_percentage,
                                                    confidence_level,
                                                    p_value=p_value,
                                                    power_value=power_value,
                                                    avg_scaled_l2=avg_scaled_l2_val,
                                                    smape_value=smape_val,
                                                )

                                                with open(pdf_file, "rb") as file:
                                                    b64_pdf = base64.b64encode(
                                                        file.read()
                                                    ).decode()

                                                # JavaScript for PDF download
                                                js = f"""
                                                    var link = document.createElement('a');
                                                    link.href = 'data:application/pdf;base64,{b64_pdf}';
                                                    link.download = 'experimental_design_report.pdf';
                                                    document.body.appendChild(link);
                                                    link.click();


                                                    document.body.removeChild(link);
                                                """
                                                streamlit_js_eval(js_expressions=js)

                                            st.success(
                                                "PDF report generated successfully!"
                                            )

                                        else:
                                            st.error(
                                                "Please select a point on the heatmap first."
                                            )

                        except Exception as e:
                            st.error(f"Error processing selected point: {str(e)}")
                            st.exception(e)
                    else:
                        st.info(
                            "Please select a point on the heatmap to see detailed information."
                        )
            elif st.session_state.simulation_button_clicked:
                st.info("Please run the simulation with updated parameters to see results.")
    else:
        # Error state when no file uploaded
        st.error("Please upload data first!")
