import streamlit as st
import pandas as pd
from Murray.main import run_geo_analysis_streamlit_app, transform_results_data
from Murray.auxiliary import cleaned_data
from Murray.plots import *
from streamlit_js_eval import streamlit_js_eval
from fpdf import FPDF
import base64
import os
from Murray.metrics import update_metrics, load_metrics
import unicodedata
import plotly.express as px
import numpy as np



ENTROPY_LOGO = "utils/Logo Entropy Dark Gray.png" 
MURRAY_LOGO = "utils/Group 105.png"
options = [ENTROPY_LOGO, MURRAY_LOGO]
sidebar_logo = ENTROPY_LOGO
main_body_logo = MURRAY_LOGO

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
    unsafe_allow_html=True
)



st.logo(sidebar_logo,size="large", icon_image=main_body_logo)


# ------------------------------------------------------------------
# Placeholder stubs to ensure functions exist before first use.
# They are overwritten by full definitions later in the file.

if 'display_multicell_results' not in globals():
    def display_multicell_results(*args, **kwargs):
        """Placeholder; real implementation defined later."""
        pass

if 'display_single_cell_results' not in globals():
    def display_single_cell_results(*args, **kwargs):
        """Placeholder; real implementation defined later."""
        pass

# ------------------------------------------------------------------

def display_single_cell_results(results, data):
    """Display single-cell analysis results (original functionality)"""
    st.subheader("📊 Analysis Results")
    
    if results:
        # Create results DataFrame
        results_data = []
        for size, result in results.items():
            results_data.append({
                'Size': size,
                'MAPE': result['MAPE'],
                'SMAPE': result['SMAPE'],
                'Holdout %': result['Holdout Percentage']
            })
        
        df_results = pd.DataFrame(results_data)
        
        # Create heatmap
        fig = px.imshow(
            df_results.set_index('Size')[['MAPE', 'SMAPE']].T,
            aspect="auto",
            title="Best Group Performance by Size",
            labels=dict(x="Group Size", y="Metric", color="Value"),
            color_continuous_scale="RdYlGn_r"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Show results table
        st.dataframe(df_results, use_container_width=True)
        
        # Find best overall group
        best_size = min(results.keys(), key=lambda x: results[x]['MAPE'])
        best_result = results[best_size]
        
        st.subheader(f"🏆 Best Overall Group (Size {best_size})")
        


def generate_pdf(treatment_group, control_group, holdout_percentage, impact_graph, 
                 weights,period_idx,mde,att,incremental,tarjet_variable,firt_day,
                 last_day,treatment_day,df,firt_report_day,second_report_day,
                 prediction_value_absolute,prediction_value_percentage,
                 lower_bound_value_absolute,lower_bound_value_percentage,
                 upper_bound_value_absolute,upper_bound_value_percentage,
                 confidence_level,p_value=None):
        """
        Generates a PDF report with explanations for each aspect.
        """
        
        
        temp_image_path = "temp_impact_graph.png"
        impact_graph.savefig(temp_image_path, bbox_inches='tight', dpi=100)
        

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.add_font("Poppins", style="B", fname="utils/Poppins-Bold.ttf", uni=True)
        pdf.add_font("Poppins", "", "utils/Poppins-Regular.ttf", uni=True)
        
        pdf.image("utils/Logo Entropy Dark Gray.png", x=10, y=10, w=20)

        
        pdf.set_font("Poppins", style='B', size=20)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 10, "Geo Murray Report", ln=True, align='C')

        

        y_actual = pdf.get_y() + 2
        pdf.line(10, y_actual, 200, y_actual)
        pdf.set_text_color(0, 0, 0)


        pdf.ln(7)

        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        pdf.multi_cell(0,5 , f"This report provides information about the experimental design on the variable '{tarjet_variable}', the experimental design was conducted for a duration of {period_idx} days. "
                            f"The data included in the design have a period of {firt_day} to {last_day} where the treatment started on {treatment_day} until {last_day}."
                            f"It includes information about the treatment group, control group, minimum detectable effect (MDE), and other relevant information.")
        


        pdf.ln(5)


        
        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Treatment Group:", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        pdf.multi_cell(0,5 , f"The treatment group consists of individuals or units that received the experimental intervention or treatment. "
                            f"The following is the description of the treatment group: ")
        
        pdf.set_font("Poppins", style='B', size=9.5)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, treatment_group)


        pdf.ln(5)


        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Control Group:", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        pdf.multi_cell(0, 5, f"The control group is used as a baseline for comparison. These are the individuals or units that did not receive the treatment "
                            f"but were otherwise similar. Here is each location of the control group: ")

        pdf.set_font("Poppins", style='B', size=9.5)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, control_group)


        pdf.ln(5)

        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Minimum Detectable Effect (MDE)", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)


        pdf.multi_cell(0, 5, f"The experimental design is based on the minimum detectable effect (MDE) which is the smallest effect that can be detected with a given level of confidence. "
                            f"In this case, the MDE is {round(mde * 100)}% for the period of {period_idx} days. "
        )
                            
        pdf.ln(5)
        
        
        if p_value is not None:
            pdf.set_font("Poppins", style='B', size=12)
            pdf.set_text_color(27, 0, 67)
            pdf.cell(200, 8, "Statistical Significance (P-Value)", ln=True)
            pdf.set_font("Poppins", size=10)
            pdf.set_text_color(33, 31, 36)
            
            
            if p_value < 0.001:
                p_value_str = f"{p_value:.6f} (p < 0.001)"
                significance = "Highly Significant"
            elif p_value < 0.01:
                p_value_str = f"{p_value:.4f} (p < 0.01)"
                significance = "Very Significant"
            elif p_value < 0.05:
                p_value_str = f"{p_value:.4f} (p < 0.05)"
                significance = "Significant"
            elif p_value < 0.1:
                p_value_str = f"{p_value:.4f} (p < 0.1)"
                significance = "Marginally Significant"
            else:
                p_value_str = f"{p_value:.4f} (p ≥ 0.1)"
                significance = "Not Significant"
            
            pdf.multi_cell(0, 5, f"The statistical significance of the minimum detectable effect is evaluated using permutation tests. "
                                f"The p-value obtained is {p_value_str}, which indicates that the result is {significance.lower()}. "
                                f"This p-value represents the probability of observing the observed effect size or larger under the null hypothesis "
                                f"that there is no true treatment effect.")
            pdf.ln(5)

        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Conversion Percentages")



        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.cell(200, 8, f"Treatment Percentage: {(100 - holdout_percentage):.2f}%", ln=True)

        pdf.cell(200, 5, f"Holdout Percentage: {holdout_percentage:.2f}%", ln=True)
        pdf.cell(200, 5, f"Treatment Percentage: {(100 - holdout_percentage):.2f}%", ln=True)
        pdf.set_font("Poppins", size=10)

        pdf.multi_cell(0, 5, "The holdout percentage represents the portion of the total conversions that belong to the control group. "
                            "The treatment percentage represents the portion of the total conversions that are allocated to the treatment group.")

        pdf.ln(5)
        

        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 10, "Control Locations and Weights:", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        

        col_width = 95  
        row_height = 8  
        header_bg = (103, 85, 130)  
        alt_row_bg = (209, 204, 217)  
        white_row_bg = (246, 246, 246)  
        text_color = (33, 31, 36)

        
        if pdf.get_y() > 250: 
            pdf.add_page()
            
        pdf.set_fill_color(*header_bg)  
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Poppins", style='B', size=10)
        pdf.cell(col_width, row_height, "Location", 1, 0, 'C', True)
        pdf.cell(col_width, row_height, "Weight", 1, 1, 'C', True)
        
        



        for i, row in weights.iterrows():
            bg_color = alt_row_bg if i % 2 else white_row_bg

            pdf.set_fill_color(*bg_color)
            pdf.set_text_color(*text_color)
            pdf.set_font("Poppins", size=10)
    
            pdf.cell(col_width, row_height, row['Control Location'], 1, 0, 'C', True)
            pdf.cell(col_width, row_height, f"{row['Weights']:.4f}", 1, 1, 'C', True)



        pdf.ln(5) 
        if pdf.get_y() > 250:
            pdf.add_page() 
        
        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 10, "Impact", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        pdf.multi_cell(0, 5, "The results show the impact of the treatment on different treatment locations. "
                            "Below is the ATT value and the lift value total of the target variable.")


        
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
        
        pdf.cell(190, title_height, title_text, border=1, ln=1, align='C', fill=True)
 
        
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
            pdf.cell(col_widths[0], row_height, label, border=1, ln=0, align='C', fill=True)
            pdf.cell(col_widths[1], row_height, f"{abs_val:,.2f}", border=1, ln=0, align='C', fill=True)
            pdf.cell(col_widths[2], row_height, f"{pct_val:,.2f}%", border=1, ln=1, align='C', fill=True)
        
        pdf.ln(4)
        pdf.set_font("Poppins", size=11)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"MDE: {mde * 100}%")
        pdf.ln(5)

        if pdf.get_y() > 250:
            pdf.add_page() 
        
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"It is important to be able to identify the impact of the intervention pre-intervention and" 
                       f"post-intervention in real values. In this case, a small table is presented where the pre-intervention"
                       f"value (with the same duration as the treatment period) and the post-intervention value are observed."
                       f"This allows for a quick and simple identification of the impact that an intervention would have in"
                       f"comparison to the locations where it is not applied (counterfactual).")
        pdf.ln(1)
        if pdf.get_y() > 210:
            pdf.add_page() 
        col_widths = [70, 60,60]
        row_height = 8

        
        header_texts = [
            "Group",
            f"Pre-treatment\n({firt_report_day} to {second_report_day})",
            f"Post-treatment\n({treatment_day} to {last_day})",
            
        ]

        
        max_lines = 0
        for txt in header_texts:
            n = txt.count('\n') + 1
            if n > max_lines:
                max_lines = n
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
                
                
                pdf.cell(col_widths[i], row_height, lines[0], border=0, ln=0, align='C')
                
                
                pdf.ln(row_height)
                pdf.set_x(current_x)  
                
                
                current_font_size = pdf.font_size_pt
                smaller_font = current_font_size * 0.7
                pdf.set_font("Poppins", "B", smaller_font)
                
                
                pdf.cell(col_widths[i], row_height, lines[1], border=0, ln=0, align='C')
                
                
                pdf.set_font("Poppins", "B", current_font_size)
                
            else:
                pdf.multi_cell(col_widths[i], row_height, txt, border=0, align='C')
            
            
            x += col_widths[i]
            pdf.set_xy(x, y_start)

        
        pdf.set_xy(x_start, y_start + max_header_height)

        pdf.set_text_color(*text_color)
        pdf.set_font("Poppins", "", 10)
        y_data_start = pdf.get_y()

        for i, row in df.iterrows():
            bg_color = alt_row_bg if i % 2 else white_row_bg
            pdf.set_fill_color(*bg_color)
            
            pdf.cell(col_widths[0], row_height, str(row["Group"]), border=1, ln=0, align='C', fill=True)
            pdf.cell(col_widths[1], row_height, f"{row['Pre-treatment']:,.2f}", border=1, ln=0, align='C', fill=True)
            pdf.cell(col_widths[2], row_height, f"{row['Post-treatment']:,.2f}", border=1, ln=1, align='C', fill=True)

       
        


        pdf.ln(9)
        if pdf.get_y() > 170:
            pdf.add_page()
            
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, "The graph below shows the aggregate effect, the point effect, and the cumulative effect. ")

        pdf.image(temp_image_path, x=10, y=pdf.get_y(), w=190)  
        

        

        
         


        pdf_output = "reporte.pdf"
        pdf.output(pdf_output, "F")


        os.remove(temp_image_path)


        return pdf_output

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
    unsafe_allow_html=True
)







st.title("Experimental Design")

# Initialize session state variables
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
if "selected_point" not in st.session_state:
    st.session_state.selected_point = None
if "last_params" not in st.session_state:
        st.session_state.last_params = {}
if "fig2" not in st.session_state:
    st.session_state.fig2 = None

    #--------------------------------------------------------------------------------------------------------------------------------

st.subheader("1. Upload file")

def style_table(df):
    return df.style.set_table_styles([
        {"selector": "thead th", "props": [
            ("font-weight", "bold"),
            ("color", "black"),
            ("background-color", "#f0f0f0"),
            ("font-size", "16px"),
            ("text-align", "center")
        ]}
    ]).set_properties(**{
        'text-align': 'center',
        'white-space': 'nowrap'
    }).set_table_attributes('class="dataframe"')


file = st.file_uploader("Choose a file ", type=["csv"])

if file is not None:
    data = pd.read_csv(file)

    if data is not None:
        st.markdown("""
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
        """, unsafe_allow_html=True)

        
        styled_table = style_table(data.head()).to_html()

        
        st.markdown(f'<div class="dataframe-container">{styled_table}</div>', unsafe_allow_html=True)


        st.text("Type the name of columns for the following parameters:")
        col1, col2, col3 = st.columns(3)

        

        def normalize_text(text):
            """Remove accents and convert to lowercase"""
            if not isinstance(text, str):
                return str(text).lower()
            return ''.join(c for c in unicodedata.normalize('NFD', text)
                          if unicodedata.category(c) != 'Mn').lower()

        def reset_states():
            st.session_state.graph_generated = False
            st.session_state.current_fig = None
            st.session_state.simulation_button_clicked = False

        # Palabras clave originales
        contains_date = ["date", "day", "time", "fecha", "dia", "tiempo"]
        contains_locations = ["location", "region", "state", "ubicacion", "region", "estado"]

        # Palabras clave normalizadas
        contains_date_norm = [normalize_text(x) for x in contains_date]
        contains_locations_norm = [normalize_text(x) for x in contains_locations]

        with col1:
            matching_column1 = next(
                (col for col in data.columns if any(p in normalize_text(col) for p in contains_date_norm)), None
            )
            col_dates = st.text_input("Date", matching_column1 if matching_column1 else "", 
                                    on_change=reset_states, key="dates")
        with col2:
            matching_column2 = next(
                (col for col in data.columns if any(q in normalize_text(col) for q in contains_locations_norm)), None
            )
            if matching_column2:
                data[matching_column2] = data[matching_column2].astype(str)
            col_locations = st.text_input("Locations", matching_column2 if matching_column2 else "", 
                                        on_change=reset_states, key="locations")
            
        with col3:
            target_columns = [
                col for col in data.columns
                if not any(
                    d in normalize_text(col) for d in contains_date_norm
                )
                and not any(
                    l in normalize_text(col) for l in contains_locations_norm
                )
            ]
            col_target = st.selectbox("Target", target_columns, on_change=reset_states, key="target")
        
        if col_dates == "" or col_locations == "" or col_target == "":
            st.warning("Please fill in all required fields (Dates, Locations, and Target).")
        elif col_dates not in data.columns or col_locations not in data.columns or col_target not in data.columns:
            st.error("Please enter correct column names.")
            st.stop()
        else:
            if 'graph_generated' not in st.session_state:
                st.session_state.graph_generated = False
            if 'current_fig' not in st.session_state:
                st.session_state.current_fig = None
            if col_dates and col_locations and col_target:
                try:
                    if col_locations in data.columns:
                        data[col_locations] = data[col_locations].astype(str)
                    cleaned = cleaned_data(data, col_target=col_target, col_locations=col_locations, col_dates=col_dates)
                except TypeError as e:
                    st.error(str(e))
                    st.stop()
                except ValueError as e:
                    st.error(str(e))
                    st.stop()
                except Exception as e:
                    st.error(str(e))
                    st.stop()



    #--------------------------------------------------------------------------------------------------------------------------------

            st.subheader("2. Data visualization")
            if "graph_button_clicked" not in st.session_state:
                st.session_state.graph_button_clicked = False

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
                    unsafe_allow_html=True
                )
                st.plotly_chart(st.session_state.fig,config={
                    'modeBarButtonsToRemove': [
                        'zoom2d',
                        'pan2d',
                        'select2d',
                        'lasso2d',
                        'resetScale2d',
                    ],
                    'displaylogo': False
                })
                


    #--------------------------------------------------------------------------------------------------------------------------------

            st.subheader("3. Experimental design")
            st.text("Parameter configuration")

            st.markdown("""
            <style>
                .stMultiSelect span[data-baseweb="tag"] {
                    background-color: #ecf2f7 !important;
                    color: black !important;
                }

            """, unsafe_allow_html=True)
            excluded_locations = st.multiselect("Select excluded locations", cleaned['location'].unique())
            
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

            maximum_treatment_percentage_pre = st.slider("Select maximum treatment percentage (%)", 5, 50, 30, help="Maximum percentage of the target variable that can be contained in the treatment group")
            maximum_treatment_percentage = maximum_treatment_percentage_pre / 100
            
            significance_level_pre = st.number_input("Select significance level (%)", min_value=1, max_value=100, value=10, step=1, help="Threshold to judge a result as statistically significant. For example, with a 10% significance level, it means you have a 90% confidence level")
            significance_level = significance_level_pre  / 100
            if significance_level > 0.20:
                st.warning("A high value could lead to false results")
            st.text("Select range of lifts")
            col1, col2, col3 = st.columns(3)
            with col1:
                delta_min = st.number_input("Lift Min:", min_value=0.00, max_value=0.9, value=0.01, step=0.01)
            with col2:
                delta_max = st.number_input("Lift Max:", min_value=0.02, max_value=1.0, value=0.15, step=0.01)
            with col3:
                delta_step = st.number_input("Lift Step:", min_value=0.00, max_value=1.0, value=0.01, step=0.01)
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
            st.text("Select range of periods")
            col1, col2, col3 = st.columns(3)
            with col1:
                period_min = st.number_input("Period Min:", min_value=1, max_value=100, value=5, step=1)
            with col2:    
                period_max = st.number_input("Period Max:", min_value=5, max_value=100, value=30, step=1)
            with col3:    
                period_step = st.number_input("Period Step:", min_value=1, max_value=100, value=5, step=1)
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
                periods_range = (period_min, period_max+1, period_step)
            
            
            
            
            

            
            # st.text("Click on the button to start simulation")

            # Multi-cell configuration
            enable_multicell = st.checkbox("Enable Multi-Cell Mode", value=False, help="Enable to select specific group sizes and get top N results per size", key="multicell_checkbox")
            
        

            multicell_config = None
            if enable_multicell:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Get available sizes based on data
                    unique_locations = cleaned['location'].unique()
                    no_locations = len(unique_locations)
                    max_group_size = round(no_locations * 0.45)
                    min_elements_in_treatment = round(no_locations * 0.10)
                    
                    available_sizes = list(range(min_elements_in_treatment, max_group_size + 1))
                    selected_sizes = st.multiselect(
                        "Select Group Sizes",
                        options=available_sizes,
                        default=available_sizes[:3] if len(available_sizes) >= 3 else available_sizes,
                        help="Choose which group sizes to evaluate",
                        key="multicell_sizes"
                    )
                
                with col2:
                    top_n_per_size = st.number_input(
                        "Top N Results per Size",
                        min_value=1,
                        max_value=10,
                        value=3,
                        help="Number of best groups to keep for each size",
                        key="multicell_top_n"
                    )
                
                if selected_sizes:
                    multicell_config = {
                        'sizes': selected_sizes,
                        'top_n': top_n_per_size
                    }
                    

            if "simulation_results" not in st.session_state:
                st.session_state.simulation_results = None
                st.session_state.sensitivity_results = None
                st.session_state.results = None

            
            if "selected_point" not in st.session_state:
                st.session_state.selected_point = None

            
            if "last_params" not in st.session_state:
                st.session_state.last_params = {}

            
            current_params = {
                "excluded_locations": excluded_locations,
                "maximum_treatment_percentage_pre": maximum_treatment_percentage_pre,
                "significance_level_pre": significance_level_pre,
                "deltas_range": (delta_min, delta_max, delta_step),
                "periods_range": (period_min, period_max+1, period_step),
                "col_target": col_target,
            }

            
            if current_params != st.session_state.last_params:
                st.session_state.simulation_button_clicked = False  
                st.session_state.selected_point = None  
                st.session_state.last_params = current_params  


            if "simulation_button_clicked" not in st.session_state:
                st.session_state.simulation_button_clicked = False

            st.text("Click on the button to start simulation")

            if st.button("Run Simulation") or st.session_state.simulation_button_clicked:
                if not st.session_state.simulation_button_clicked:
                    st.session_state.simulation_button_clicked = True
                    
                    update_metrics("experimental_design")
                    
                    with st.spinner('Running simulation...'):
                        # Reset multicell mode at start of simulation
                        st.session_state.is_multicell_mode = False
                        
                        results = run_geo_analysis_streamlit_app(
                            data=cleaned,
                            excluded_locations=excluded_locations,
                            maximum_treatment_percentage=maximum_treatment_percentage,
                            significance_level=significance_level,
                            deltas_range=deltas_range,
                            periods_range=periods_range,
                            multicell_config=multicell_config
                        )

                        

                    results_by_size = transform_results_data(results['simulation_results'])
                    
                    
                    
                    st.session_state.results = results
                    st.session_state.simulation_results = results_by_size
                    st.session_state.sensitivity_results = results['sensitivity_results']
                    # Store full results for multicell mode
                    st.session_state.full_results = results
                    st.session_state.multicell_config = multicell_config if enable_multicell else None
                    periods = list(np.arange(*periods_range))

                    # Handle multi-cell results display
                    if enable_multicell and multicell_config and results['simulation_results']:
                        # Set multicell mode in session state
                        st.session_state.is_multicell_mode = True
                        st.subheader("📊 Multi-Cell Analysis Results")
                        
                        if results['simulation_results']:
                            # Show which sizes were processed vs skipped
                            all_selected_sizes = multicell_config.get('selected_sizes', [])
                            processed_sizes = list(results['simulation_results'].keys())
                            skipped_sizes = [size for size in all_selected_sizes if size not in processed_sizes]
                            
                            st.success(f"✅ Found valid results for {len(processed_sizes)} group sizes")
                            
                            if skipped_sizes:
                                st.warning(f"⚠️ The following sizes were skipped due to insufficient data: {skipped_sizes}")
                            
                            st.info(f"📊 Processed sizes: {processed_sizes}")
                            
                            # Create comprehensive results table
                            st.subheader("📋 Complete Multi-Cell Results")
                            
                            # Get sensitivity results for MDE and p-value
                            sensitivity_data = results.get('sensitivity_results', {})
                            
                            # Get all available periods
                            available_periods = set()
                            for size_data in sensitivity_data.values():
                                available_periods.update(size_data.keys())
                            available_periods = sorted(list(available_periods))
                            
                            # Period selector
                            if available_periods:
                                selected_period = st.selectbox(
                                    "🕐 Select Period to Display:",
                                    options=available_periods,
                                    index=0,
                                    help="Choose the treatment period to analyze. Different periods may show different MDE values.",
                                    key="multicell_period_selector"
                                )
                                
                                st.info(f"📊 Showing results for Period: **{selected_period} days**")
                            else:
                                selected_period = None
                                st.warning("No sensitivity data available for period selection.")
                            
                            detailed_results = []
                            
                            for size, data in results['simulation_results'].items():
                                if isinstance(data, list):
                                    for idx, group in enumerate(data):
                                        # Get MDE and p-value from sensitivity results for selected period
                                        mde_info = {}
                                        if size in sensitivity_data and selected_period is not None:
                                            period_data = sensitivity_data[size].get(selected_period, {})
                                            mde_value = period_data.get('MDE')
                                            p_value = period_data.get('P-Value')
                                            
                                            mde_info = {
                                                'MDE': f"{mde_value:.3f}" if mde_value is not None else "N/A",
                                                'Period': selected_period,
                                                'P-Value': f"{p_value:.4f}" if p_value is not None else "N/A"
                                            }
                                        else:
                                            mde_info = {'MDE': "N/A", 'Period': "N/A", 'P-Value': "N/A"}
                                        
                                        detailed_results.append({
                                            'Size': size,
                                            'Rank': idx + 1,
                                            'Treatment Group': ', '.join(group['Best Treatment Group']),
                                            'Control Group': ', '.join(group['Control Group']),
                                            'MAPE': f"{group['MAPE']:.4f}",
                                            'SMAPE': f"{group['SMAPE']:.4f}",
                                            'Holdout %': f"{group['Holdout Percentage']:.2f}%",
                                            'MDE': mde_info['MDE'],
                                            'Period': mde_info['Period'],
                                            'P-Value': mde_info['P-Value']
                                        })
                            
                            if detailed_results:
                                df_detailed = pd.DataFrame(detailed_results)
                                
                                # Sort by Size and then by Rank
                                df_detailed = df_detailed.sort_values(['Size', 'Rank'])
                                
                                # Add styling info
                                if selected_period:
                                    st.caption(f"💡 **Note:** MDE and P-Value shown for {selected_period}-day treatment period. Change the period selector above to see different results.")
                                
                                # Style the dataframe
                                st.dataframe(
                                    df_detailed, 
                                    use_container_width=True,
                                    height=min(600, len(detailed_results) * 35 + 50)  # Dynamic height
                                )
                                
                                # Add download button for results
                                csv = df_detailed.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Results as CSV",
                                    data=csv,
                                    file_name=f"multicell_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                                
                                # Show summary statistics
                                st.subheader("📈 Summary Statistics")
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("Total Groups", len(detailed_results))
                                with col2:
                                    avg_mape = df_detailed[df_detailed['MAPE'] != 'N/A']['MAPE'].astype(float).mean()
                                    st.metric("Avg MAPE", f"{avg_mape:.4f}")
                                with col3:
                                    avg_smape = df_detailed[df_detailed['SMAPE'] != 'N/A']['SMAPE'].astype(float).mean()
                                    st.metric("Avg SMAPE", f"{avg_smape:.4f}")
                                with col4:
                                    valid_mdes = df_detailed[df_detailed['MDE'] != 'N/A']['MDE'].astype(float)
                                    avg_mde = valid_mdes.mean() if len(valid_mdes) > 0 else 0
                                    st.metric("Avg MDE", f"{avg_mde:.3f}")
                                
                            else:
                                st.warning("No detailed results to display.")
                        else:
                            st.warning("⚠️ No multi-cell results available.")
                        
                        st.stop()  # Don't continue to single-cell heatmap logic
                    else:
                        # Single-cell mode - generate heatmap
                        st.session_state.is_multicell_mode = False
                        try:
                            st.session_state.fig2 = plot_mde_results(results_by_size, results['sensitivity_results'], periods)
                        except ValueError as e:
                            st.error(f"Error generating the heatmap: {e}")
                            st.stop()
                    

                # Only show single-cell results if not in multicell mode
                if (st.session_state.simulation_results is not None and 
                    not getattr(st.session_state, 'is_multicell_mode', False)):


                    st.markdown(
                        """
                        <style>
                        .js-plotly-plot .plotly .cursor-move {
                            cursor: default !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )


                    st.write('<h4 style="text-align: center;"> Geo Murray MDE Heatmap</h4>', unsafe_allow_html=True)
                    fig2 = st.session_state.fig2
                    if fig2 is None or not hasattr(fig2, 'to_dict'):
                        st.error("⚠️ Heatmap could not be generated for these parameters.")
                        event = st.empty()
                    else:
                        event = st.plotly_chart(
                            fig2,
                            key="heatmap",
                            on_select="rerun",
                            config={
                                'modeBarButtonsToRemove': [
                                    'zoom2d',
                                    'pan2d',
                                    'select2d',
                                    'lasso2d',
                                    'resetScale2d',
                                ],
                                'displaylogo': False
                            }
                        )
                    



                    selected_point = event.selection
                   
                    

       

                    if selected_point and "points" in selected_point and len(selected_point["points"]) > 0:
                        point = selected_point["points"][0]



                        if "x" in point and "y" in point:
                            st.session_state.selected_point = point
                            

                    if st.session_state.selected_point:
                        x_value, y_value = st.session_state.selected_point["x"], st.session_state.selected_point["y"]
                        treatment_percentage = round(100 - float(y_value.strip('%')),2)
                        try:
                            if isinstance(x_value, str) and "Day-" in x_value:
                                period_idx = int(x_value.replace("Day-", "")) 

                            else:
                                period_idx = None

                            if isinstance(y_value, (int, float)):
                                
                                y_value_str = f"{treatment_percentage:.2f}%"

                            else:
                                y_value_str = str(f'{treatment_percentage}%')

                            st.write(f"###### Locations with a treatment percentage of: {y_value_str}")

                            location = None
                            for loc, data in st.session_state.simulation_results.items():

                                holdout_str = f"{data['Holdout Percentage']:.2f}%"
                                if holdout_str == y_value:
                                    location = loc
                                    break

                            if location is None:
                                st.write(f"Error: Location not found for the holdout percentage: {y_value_str}")
                            else:
                                treatment_group = st.session_state.simulation_results.get(location, {}).get('Best Treatment Group', 'N/A')
                                control_group = st.session_state.simulation_results.get(location, {}).get('Control Group', 'N/A')
                                st.write(f"- **Treatment group:** {treatment_group}")
                                st.write(f"- **Control group:** {control_group}")
                               
                                mde = 'N/A'
                                if period_idx is not None and y_value is not None:
                                    y_value_float = float(y_value.strip('%')) if isinstance(y_value, str) else float(y_value)

                                    
                                    matching_size = None
                                    for size, data in st.session_state.simulation_results.items():

                                        if abs(float(data['Holdout Percentage']) - y_value_float) < 0.01:
                                            matching_size = size
                                            break
                                    
                                    if matching_size is not None:
                                        mde = st.session_state.sensitivity_results[matching_size][period_idx]['MDE']
                                st.write(f"- **Minimum Detectable Effect (MDE):** {round(mde*100)}%")
                                #st.plotly_chart(plot_metrics(st.session_state.results),use_container_width=True)
                                random_sate = cleaned['location'].unique()[0]
                                filtered_data = cleaned[cleaned['location'] == random_sate]
                                firt_day = filtered_data['time'].min()
                                last_day = filtered_data['time'].max()
                                second_report_day = last_day - pd.Timedelta(days=period_idx)
                                firt_report_day = last_day - pd.Timedelta(days=(period_idx*2)-1)
                                treatment_day = last_day - pd.Timedelta(days=period_idx-1)
                                last_day = last_day.strftime('%Y-%m-%d')
                                firt_day = firt_day.strftime('%Y-%m-%d')
                                firt_report_day = firt_report_day.strftime('%Y-%m-%d')
                                second_report_day = second_report_day.strftime('%Y-%m-%d')

                                treatment_day = treatment_day.strftime('%Y-%m-%d')
                               
                                
                                

                                
                                holdout_percentage = st.session_state.simulation_results[location]['Holdout Percentage']
                
                                treatment_states = treatment_group.split(',') 
                                length_treatment = len(treatment_states)
                               
                                
                                        


                                
                                
                                st.subheader("4. Generate report of results")
                                st.write("Click on the button to generate and download the PDF report.")
                                if st.button("Generate and Download PDF"):
                                    with st.spinner("Generating report..."):
                                        if "selected_point" in st.session_state and st.session_state.selected_point:

                                            point = st.session_state.selected_point
                                            y_value = point["y"]
                                            y_value_str = f"{y_value:.2f}%" if isinstance(y_value, (int, float)) else str(y_value)

                                            if st.session_state.results is None:
                                                st.error("No results available for report generation.")
                                                st.stop()

                                            # Get the best group for the selected size
                                            best_group = None
                                            for size, data in st.session_state.simulation_results.items():
                                                if abs(float(data['Holdout Percentage']) - float(y_value.strip('%'))) < 0.01:
                                                    best_group = data
                                                    break

                                            if best_group is None:
                                                st.error("Could not find matching group for report generation.")
                                                st.stop()

                                            # Extract data for PDF generation
                                            treatment_group = best_group['Best Treatment Group']
                                            control_group = best_group['Control Group']
                                            weights = best_group['Weights']
                                            y_original = best_group['Actual Target Metric (y)']
                                            predictions = best_group['Predictions']

                                            # Create impact graph
                                            impact_graph = plot_metrics(st.session_state.results)

                                            # Generate PDF
                                            pdf_bytes = generate_pdf(
                                                treatment_group=treatment_group,
                                                control_group=control_group,
                                                holdout_percentage=holdout_percentage,
                                                impact_graph=impact_graph,
                                                weights=weights,
                                                period_idx=period_idx,
                                                mde=mde,
                                                att=None,  # Not available in current implementation
                                                incremental=None,  # Not available in current implementation
                                                tarjet_variable=col_target,
                                                firt_day=firt_day,
                                                last_day=last_day,
                                                treatment_day=treatment_day,
                                                df=cleaned,
                                                firt_report_day=firt_report_day,
                                                second_report_day=second_report_day,
                                                prediction_value_absolute=None,  # Not available in current implementation
                                                prediction_value_percentage=None,  # Not available in current implementation
                                                lower_bound_value_absolute=None,  # Not available in current implementation
                                                lower_bound_value_percentage=None,  # Not available in current implementation
                                                upper_bound_value_absolute=None,  # Not available in current implementation
                                                upper_bound_value_percentage=None,  # Not available in current implementation
                                                confidence_level=1-significance_level,
                                                p_value=None  # Not available in current implementation
                                            )

                                            # Download button
                                            st.download_button(
                                                label="Download PDF Report",
                                                data=pdf_bytes,
                                                file_name=f"murray_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                                mime="application/pdf"
                                            )

                                            st.success("PDF report generated successfully!")

                                        else:
                                            st.error("Please select a point on the heatmap first.")

                        except Exception as e:
                            st.error(f"Error processing selected point: {str(e)}")
                            st.exception(e)

                    else:
                        st.info("Please select a point on the heatmap to see detailed information.")

                else:
                    pass
                    # st.info("Please run the simulation first to see results.")

            else:
                pass
                # st.info("Please configure parameters and click 'Run Simulation' to start the analysis.")
        
        # Handle multicell results display from session state (when changing period selector)
        if (getattr(st.session_state, 'is_multicell_mode', False) and 
            hasattr(st.session_state, 'full_results') and 
            st.session_state.full_results is not None):
            
            results = st.session_state.full_results
            multicell_config = getattr(st.session_state, 'multicell_config', None)
            
            if multicell_config and results.get('simulation_results'):
                # Show which sizes were processed vs skipped
                all_selected_sizes = multicell_config.get('selected_sizes', [])
                processed_sizes = list(results['simulation_results'].keys())
                skipped_sizes = [size for size in all_selected_sizes if size not in processed_sizes]
                
                # st.success(f"Found valid results for {len(processed_sizes)} group sizes")
                
                if skipped_sizes:
                    st.warning(f"The following sizes were skipped due to insufficient data: {skipped_sizes}")
                
                # st.info(f"Processed sizes: {processed_sizes}")
                
                # Create comprehensive results table
                st.subheader("Multi-Cell Results")
                
                # Get sensitivity results for MDE and p-value
                sensitivity_data = results.get('sensitivity_results', {})
                
                # Get all available periods
                available_periods = set()
                for size_data in sensitivity_data.values():
                    available_periods.update(size_data.keys())
                available_periods = sorted(list(available_periods))
                
                # Period selector
                if available_periods:
                    selected_period = st.selectbox(
                        "Select Period to Display:",
                        options=available_periods,
                        index=0,
                        help="Choose the treatment period to analyze. Different periods may show different MDE values.",
                        key="multicell_period_selector_persistent"
                    )
                    
                    # st.info(f"Showing results for Period: **{selected_period} days**")
                else:
                    selected_period = None
                    st.warning("No sensitivity data available for period selection.")
                
                detailed_results = []
                
                for size, data in results['simulation_results'].items():
                    if isinstance(data, list):
                        for idx, group in enumerate(data):
                            # Get MDE and p-value from sensitivity results for selected period
                            mde_info = {}
                            if size in sensitivity_data and selected_period is not None:
                                period_data = sensitivity_data[size].get(selected_period, {})
                                mde_value = period_data.get('MDE')
                                p_value = period_data.get('P-Value')
                                
                                mde_info = {
                                    'MDE': f"{mde_value:.3f}" if mde_value is not None else "N/A",
                                    'Period': selected_period,
                                    'P-Value': f"{p_value:.4f}" if p_value is not None else "N/A"
                                }
                            else:
                                mde_info = {'MDE': "N/A", 'Period': "N/A", 'P-Value': "N/A"}
                            
                            detailed_results.append({
                                'Size': size,
                                'Rank': idx + 1,
                                'Treatment Group': ', '.join(group['Best Treatment Group']),
                                'Control Group': ', '.join(group['Control Group']),
                                'MAPE': f"{group['MAPE']:.4f}",
                                'SMAPE': f"{group['SMAPE']:.4f}",
                                'Holdout %': f"{group['Holdout Percentage']:.2f}%",
                                'MDE': mde_info['MDE'],
                                'Period': mde_info['Period'],
                                'P-Value': mde_info['P-Value']
                            })
                
                if detailed_results:
                    df_detailed = pd.DataFrame(detailed_results)
                    
                    # Sort by Size and then by Rank
                    df_detailed = df_detailed.sort_values(['Size', 'Rank'])
                    
                    # Add styling info
                    # if selected_period:
                        # st.caption(f"💡 **Note:** MDE and P-Value shown for {selected_period} days treatment period. Change the period selector above to see different results.")
                    
                    # Style the dataframe
                    st.dataframe(
                        df_detailed, 
                        use_container_width=True,
                        height=min(600, len(detailed_results) * 35 + 50)  # Dynamic height
                    )
                    
                    # Add download button for results
                    csv = df_detailed.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv,
                        file_name=f"multicell_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # Show summary statistics
                    st.subheader("📈 Summary Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Groups", len(detailed_results))
                    with col2:
                        avg_mape = df_detailed[df_detailed['MAPE'] != 'N/A']['MAPE'].astype(float).mean()
                        st.metric("Avg MAPE", f"{avg_mape:.4f}")
                    with col3:
                        avg_smape = df_detailed[df_detailed['SMAPE'] != 'N/A']['SMAPE'].astype(float).mean()
                        st.metric("Avg SMAPE", f"{avg_smape:.4f}")
                    with col4:
                        valid_mdes = df_detailed[df_detailed['MDE'] != 'N/A']['MDE'].astype(float)
                        avg_mde = valid_mdes.mean() if len(valid_mdes) > 0 else 0
                        st.metric("Avg MDE", f"{avg_mde:.3f}")
                    
                else:
                    st.warning("No detailed results to display.")
    else:
        st.error("❌ Please upload data first!")

def display_multicell_results(results, multicell_config):
    """Display multi-cell analysis results"""
    st.subheader("📊 Multi-Cell Analysis Results")
    
    if not results:
        st.warning("⚠️ No multi-cell results available. This might be due to:")
        st.write("- Not enough locations to form groups of the selected sizes")
        st.write("- Data quality issues preventing group formation")
        st.write("- All selected group sizes were skipped due to missing values")
        return
    
    # Create heatmap of best group per size
    if results:
        sizes = list(results.keys())
        best_groups_per_size = []
        
        for size in sizes:
            if results[size]:  # Check if there are results for this size
                best_group = results[size][0]  # First group is the best (lowest MAPE)
                best_groups_per_size.append({
                    'Size': size,
                    'MAPE': best_group['MAPE'],
                    'SMAPE': best_group['SMAPE'],
                    'Holdout %': best_group['Holdout Percentage']
                })
        
        if best_groups_per_size:
            st.success(f"✅ Found valid results for {len(best_groups_per_size)} group sizes")
            
            # Show which sizes were processed vs skipped
            all_selected_sizes = multicell_config.get('selected_sizes', [])
            processed_sizes = list(results.keys())
            skipped_sizes = [size for size in all_selected_sizes if size not in processed_sizes]
            
            if skipped_sizes:
                st.warning(f"⚠️ The following sizes were skipped due to insufficient data: {skipped_sizes}")
            
            st.info(f"📊 Processed sizes: {processed_sizes}")
            
            # Create heatmap only if we have multiple sizes
            df_heatmap = pd.DataFrame(best_groups_per_size)
            
            if len(best_groups_per_size) > 1:
                fig = px.imshow(
                    df_heatmap.set_index('Size')[['MAPE', 'SMAPE']].T,
                    aspect="auto",
                    title="Best Group Performance by Size",
                    labels=dict(x="Group Size", y="Metric", color="Value"),
                    color_continuous_scale="RdYlGn_r"
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Only one group size available, skipping heatmap.")
            
            # Show best group per size table
            st.subheader("🏆 Best Group per Size")
            st.dataframe(df_heatmap, use_container_width=True)
            
            # Allow user to select a size to see detailed results
            selected_size = st.selectbox(
                "Select size to view detailed results:",
                options=sizes,
                format_func=lambda x: f"Size {x} ({len(results[x])} groups)",
                key="multicell_size_selector"
            )
            
            if selected_size and results[selected_size]:
                st.subheader(f"📋 Top {multicell_config['top_n']} Groups for Size {selected_size}")
                
                # Create detailed results table
                detailed_results = []
                for idx, group in enumerate(results[selected_size]):
                    detailed_results.append({
                        'Rank': idx + 1,
                        'Treatment Group': ', '.join(group['Best Treatment Group']),
                        'Control Group': ', '.join(group['Control Group']),
                        'MAPE': f"{group['MAPE']:.4f}",
                        'SMAPE': f"{group['SMAPE']:.4f}",
                        'Holdout %': f"{group['Holdout Percentage']:.2f}%"
                    })
                
                df_detailed = pd.DataFrame(detailed_results)
                st.dataframe(df_detailed, use_container_width=True)
                
                # Show plots for the best group of selected size
                if results[selected_size]:
                    best_group = results[selected_size][0]
                    st.subheader(f"📈 Best Group Analysis (Size {selected_size})")
                    
                    # Use existing plot functions
                    try:
                        # Use the existing plot_metrics function if we have the original results
                        if hasattr(st.session_state, 'results') and st.session_state.results:
                            fig_metrics = plot_metrics(st.session_state.results)
                            st.pyplot(fig_metrics)
                        else:
                            # Fallback to simple data display
                            st.write("**Treatment Group:**", ', '.join(best_group['Best Treatment Group']))
                            st.write("**Control Group:**", ', '.join(best_group['Control Group']))
                            st.write("**MAPE:**", f"{best_group['MAPE']:.4f}")
                            st.write("**SMAPE:**", f"{best_group['SMAPE']:.4f}")
                    except Exception as e:
                        st.warning(f"Could not create plots: {str(e)}")
                        # Fallback to simple data display
                        st.write("**Treatment Group:**", ', '.join(best_group['Best Treatment Group']))
                        st.write("**Control Group:**", ', '.join(best_group['Control Group']))
                        st.write("**MAPE:**", f"{best_group['MAPE']:.4f}")
                        st.write("**SMAPE:**", f"{best_group['SMAPE']:.4f}")





