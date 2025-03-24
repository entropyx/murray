import streamlit as st
import pandas as pd
from Murray.main import run_geo_analysis_streamlit_app, transform_results_data
from Murray.auxiliary import cleaned_data
from Murray.plots import *
from streamlit_js_eval import streamlit_js_eval
from fpdf import FPDF
import base64
import os


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
    <a class='custom-link' href="https://entropy.tech/murray/" target="_blank">Murray Documentation</a>
    """,
    unsafe_allow_html=True
)



st.logo(sidebar_logo,size="large", icon_image=main_body_logo)



def generate_pdf(treatment_group, control_group, holdout_percentage, impact_graph, 
                 weights,period_idx,mde,att,incremental,tarjet_variable,firt_day,
                 last_day,treatment_day,df,firt_report_day,second_report_day):
        """
        Generates a PDF report with explanations for each aspect.
        """
        
        
        temp_image_path = "temp_impact_graph.png"
        impact_graph.savefig(temp_image_path, bbox_inches='tight', dpi=300)
        

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
        
        pdf.set_font("Poppins", style='B', size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.cell(200, 5, f"ATT: {att:,.2f}", ln=True)
        pdf.cell(200, 5, f"Lift total: {incremental:,.2f}", ln=True)
        pdf.cell(200, 5, f"Percentage Lift: {round(mde * 100)}%", ln=True)


        pdf.ln(4)
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

        

        def reset_states():
            st.session_state.graph_generated = False
            st.session_state.current_fig = None
            st.session_state.simulation_button_clicked = False

        with col1:
            contains_date = ["date", "day", "time"]
            matching_column1 = next((col for col in data.columns if any(p in col.lower() for p in contains_date)), None)
            col_dates = st.text_input("Dates", matching_column1 if matching_column1 else "", 
                                    on_change=reset_states, key="dates")
        with col2:
            contains_locations = ["location", "region", "state"]
            matching_column2 = next((col for col in data.columns if any(q in col.lower() for q in contains_locations)), None)
            if matching_column2:
                data[matching_column2] = data[matching_column2].astype(str)
            col_locations = st.text_input("Locations", matching_column2 if matching_column2 else "", 
                                        on_change=reset_states, key="locations")
        with col3:
            target_columns = [col for col in data.columns 
                            if not any(d in col.lower() for d in contains_date) 
                            and not any(l in col.lower() for l in contains_locations)]
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
                    data1 = cleaned_data(data, col_target=col_target, col_locations=col_locations, col_dates=col_dates)
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
                fig = plot_geodata(data1)
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
            excluded_locations = st.multiselect("Select excluded locations", data1['location'].unique())
            
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
                delta_max = st.number_input("Lift Max:", min_value=0.02, max_value=1.0, value=0.3, step=0.01)
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
                period_max = st.number_input("Period Max:", min_value=5, max_value=100, value=40, step=1)
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
            
            
            
            
            

            
            st.text("Click on the button to start simulation")



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


            if st.button("Run simulation") and not st.session_state.simulation_button_clicked:
                st.session_state.simulation_button_clicked = True  

                st.markdown(
                    """
                    <style>
                        
                        div[data-testid="stProgress"] > div > div > div {
                            background-color: #D8E5EF !important;
                        }

                        
                        div[data-testid="stProgress"] > div > div > div > div {
                            background-color: #8BB0D0 !important;
                        }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )


                progress_bar_1 = st.progress(0)
                status_text_1 = st.empty()
                progress_bar_2 = st.progress(0)
                status_text_2 = st.empty()        

                
                try:
                    results = run_geo_analysis_streamlit_app(
                        data=data1,
                        excluded_locations=excluded_locations,
                        maximum_treatment_percentage=maximum_treatment_percentage,
                        significance_level=significance_level,
                        deltas_range=deltas_range,
                        periods_range=periods_range,
                        progress_bar_1=progress_bar_1,
                        status_text_1=status_text_1,
                        progress_bar_2=progress_bar_2,
                        status_text_2=status_text_2
                    )
                    

                    

                except ValueError as e:  
                    st.error(str(e))
                    st.stop()

                except Exception as e:  
                    st.error(f"An unexpected error occurred: {str(e)}")
                    st.stop()
                
                results_by_size = transform_results_data(results['simulation_results'])
                
                
                
                st.session_state.results = results
                st.session_state.simulation_results = results_by_size
                st.session_state.sensitivity_results = results['sensitivity_results']
                periods = list(np.arange(*periods_range))

                try:
                    
                    st.session_state.fig2 = plot_mde_results(results_by_size, results['sensitivity_results'], periods)
                except ValueError as e:
                    st.error(f"Error generating the heatmap: {e}")
                    st.stop()
                

            if st.session_state.simulation_results is not None:


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
                event = st.plotly_chart(fig2,key="heatmap",on_select="rerun",config={
                    'modeBarButtonsToRemove': [
                        'zoom2d',
                        'pan2d',
                        'select2d',
                        'lasso2d',
                        'resetScale2d',
                    ],
                    'displaylogo': False
                })
                



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
                            st.write(f"- **Minimum Detectable Effect (MDE):** {mde}%")
                            st.plotly_chart(plot_metrics(st.session_state.results),use_container_width=True)
                            random_sate = data1['location'].unique()[0]
                            filtered_data = data1[data1['location'] == random_sate]
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
                           
                            
                            

                            
                            
                           
                            
                                    


                            
                            
                            st.subheader("4. Generate report of results")
                            st.write("Click on the button to generate and download the PDF report.")
                            if st.button("Generate and Download PDF"):
                                if "selected_point" in st.session_state and st.session_state.selected_point:

                                    point = st.session_state.selected_point
                                    y_value = point["y"]
                                    y_value_str = f"{y_value:.2f}%" if isinstance(y_value, (int, float)) else str(y_value)

                                    if st.session_state.results is None:
                                        st.error("Please run the simulation first before generating a PDF.")
                                        st.stop()

                                        

                                    location = None
                                    for loc, data in st.session_state.simulation_results.items():
                                        holdout_str = f"{data['Holdout Percentage']:.2f}%"
                                        if holdout_str == y_value_str:
                                            location = loc
                                            break

                                    if location is None:
                                        st.write(f"Location not found for the holdout percentage: {y_value_str}")
                                    else:
                                        treatment_group = st.session_state.simulation_results[location]['Best Treatment Group']
                                        control_group = st.session_state.simulation_results[location]['Control Group']
                                        holdout_percentage = st.session_state.simulation_results[location]['Holdout Percentage']
                                        pre_treatment, pre_counterfactual, post_treatment, post_counterfactual,impact_graph,att,incremental = plot_impact_report(st.session_state.results, period_idx, holdout_percentage)
                                        weights = print_weights(st.session_state.results, treatment_percentage)
                                        df = pd.DataFrame(
                                            {
                                                "Group": ["Treatment", "Counterfactual (control)", "Absolute difference"],
                                                "Pre-treatment": [np.sum(pre_treatment),np.sum(pre_counterfactual), np.abs(np.sum(pre_treatment)-np.sum(pre_counterfactual))],
                                                "Post-treatment": [np.sum(post_treatment), np.sum(post_counterfactual),np.abs(np.sum(post_treatment)- np.sum(post_counterfactual))]
                                                
                                            }
                                        )
                                        




                                        
                                        


                                        pdf_file = generate_pdf(treatment_group, control_group, holdout_percentage, impact_graph,weights,period_idx,mde,att,incremental,col_target,firt_day,last_day,treatment_day,df,firt_report_day,second_report_day)
                                        
                                        


                                        with open(pdf_file, "rb") as file:
                                            b64_pdf = base64.b64encode(file.read()).decode()
                                        
                                        js = f"""
                                            var link = document.createElement('a');
                                            link.href = 'data:application/pdf;base64,{b64_pdf}';
                                            link.download = 'experimental_design_report.pdf';
                                            document.body.appendChild(link);
                                            link.click();


                                            document.body.removeChild(link);
                                        """
                                        streamlit_js_eval(js_expressions=js)


                    except Exception as e:
                        st.error(f"Error recovering information: {str(e)}")
                        st.error(f"Error type: {type(e).__name__}")
                        
                        import traceback
                        st.error(f"Full error trace:\n{traceback.format_exc()}")  
                        st.stop()
                  




