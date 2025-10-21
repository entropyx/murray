"""
PDF Report Generator for Experimental Design Results
Simplified version for Murray Web UI
"""
from fpdf import FPDF
import pandas as pd
import os


def generate_design_pdf(
    treatment_group,
    control_group,
    weights_df,
    mde,
    p_value,
    power,
    holdout_percentage,
    treatment_period,
    significance_level=0.05
):
    """
    Generate PDF report for experimental design results

    Parameters:
    - treatment_group: str, comma-separated treatment locations
    - control_group: str, comma-separated control locations
    - weights_df: DataFrame with columns ['Control Location', 'Weights']
    - mde: float, Minimum Detectable Effect
    - p_value: float, statistical p-value
    - power: float, statistical power
    - holdout_percentage: float, percentage of locations in treatment
    - treatment_period: int, number of days for treatment
    - significance_level: float, alpha level (default 0.05)
    """

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Check if custom fonts exist, otherwise use built-in
    font_path = "../utils/Poppins-Bold.ttf"
    logo_path = "../utils/Logo Entropy Dark Gray.png"

    if os.path.exists(font_path):
        pdf.add_font("Poppins", style="B", fname="../utils/Poppins-Bold.ttf", uni=True)
        pdf.add_font("Poppins", "", "../utils/Poppins-Regular.ttf", uni=True)
        font_family = "Poppins"
    else:
        font_family = "Arial"

    # Header with logo if available
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=10, w=20)

    pdf.set_font(font_family, style="B", size=20)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 10, "Murray Experimental Design Report", ln=True, align="C")

    # Line separator
    y_actual = pdf.get_y() + 2
    pdf.line(10, y_actual, 200, y_actual)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(7)

    # Introduction
    pdf.set_font(font_family, size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(
        0,
        5,
        "This report summarizes the recommended experimental design for your geo experiment. "
        "The analysis has identified optimal treatment and control groups to maximize statistical power.",
    )
    pdf.ln(5)

    # Treatment Group
    pdf.set_font(font_family, style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 8, "Treatment Group:", ln=True)
    pdf.set_font(font_family, size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(0, 5, "Locations that will receive the intervention:")
    pdf.set_font(font_family, style="B", size=9.5)
    pdf.multi_cell(0, 5, treatment_group)
    pdf.ln(5)

    # Control Group
    pdf.set_font(font_family, style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 8, "Control Group:", ln=True)
    pdf.set_font(font_family, size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(0, 5, "Locations that will serve as baseline comparison:")
    pdf.set_font(font_family, style="B", size=9.5)
    pdf.multi_cell(0, 5, control_group)
    pdf.ln(5)

    # Experimental Parameters
    pdf.set_font(font_family, style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 8, "Experimental Parameters", ln=True)
    pdf.set_font(font_family, size=10)
    pdf.set_text_color(33, 31, 36)

    pdf.cell(200, 5, f"Treatment Period: {treatment_period} days", ln=True)
    pdf.cell(200, 5, f"Holdout Percentage: {holdout_percentage:.2f}%", ln=True)
    pdf.cell(200, 5, f"Significance Level: {significance_level * 100:.0f}% (alpha = {significance_level})", ln=True)
    pdf.ln(5)

    # MDE
    pdf.set_font(font_family, style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 8, "Minimum Detectable Effect (MDE)", ln=True)
    pdf.set_font(font_family, size=10)
    pdf.set_text_color(33, 31, 36)
    pdf.multi_cell(
        0,
        5,
        f"The smallest effect that can be reliably detected with this experimental design is {mde * 100:.2f}%. "
        "This represents the minimum percentage change in your target metric that the experiment can identify as statistically significant.",
    )
    pdf.ln(5)

    # P-Value
    if p_value is not None:
        pdf.set_font(font_family, style="B", size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Statistical Significance (P-Value)", ln=True)
        pdf.set_font(font_family, size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(
            0,
            5,
            f"P-Value: {p_value:.4f}. " +
            ("This indicates a statistically significant result." if p_value < significance_level
             else "This does not reach statistical significance."),
        )
        pdf.ln(5)

    # Statistical Power
    if power is not None:
        pdf.set_font(font_family, style="B", size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Statistical Power", ln=True)
        pdf.set_font(font_family, size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(
            0,
            5,
            f"Power: {power * 100:.1f}%. Statistical power represents the probability of detecting a true effect. "
            f"A power of {power * 100:.1f}% means there is a {power * 100:.1f}% chance of detecting the MDE if it truly exists.",
        )
        pdf.ln(5)

    # Control Locations and Weights
    if pdf.get_y() > 250:
        pdf.add_page()

    pdf.set_font(font_family, style="B", size=12)
    pdf.set_text_color(27, 0, 67)
    pdf.cell(200, 10, "Control Locations and Weights:", ln=True)

    # Table
    col_width = 95
    row_height = 8
    header_bg = (27, 0, 67)

    pdf.set_fill_color(*header_bg)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_family, style="B", size=10)
    pdf.cell(col_width, row_height, "Location", 1, 0, "C", True)
    pdf.cell(col_width, row_height, "Weight", 1, 1, "C", True)

    pdf.set_text_color(33, 31, 36)
    pdf.set_font(font_family, size=10)

    for idx, row in weights_df.iterrows():
        bg_color = (240, 240, 240) if idx % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg_color)
        pdf.cell(col_width, row_height, str(row["Control Location"]), 1, 0, "C", True)
        pdf.cell(col_width, row_height, f"{row['Weights']:.4f}", 1, 1, "C", True)

    # Footer
    pdf.ln(10)
    pdf.set_font(font_family, size=8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(
        0,
        4,
        "Generated by Murray - Geo Experimental Design Tool\n"
        "This report provides recommendations based on synthetic control methodology."
    )

    # Save PDF
    pdf_output = "murray_design_report.pdf"
    pdf.output(pdf_output, "F")

    return pdf_output
