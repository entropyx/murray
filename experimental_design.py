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



def generate_pdf(treatment_group, control_group, holdout_percentage, impact_graph, weights,period_idx,mde,att,incremental,tarjet_variable,firt_day,last_day,treatment_day):
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
        header_bg = (103, 85, 130)  # Morado oscuro para los títulos
        alt_row_bg = (209, 204, 217)  # Morado pastel
        white_row_bg = (246, 246, 246)  # Gris claro
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


        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 10, "Impact", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        pdf.multi_cell(0, 5, "The results show the impact of the treatment on different treatment locations. "
                            "The graph below shows the aggregate effect, the point effect, and the cumulative effect. "
                            "Below is the ATT value and the lift value total of the target variable, as well as the graphs of impact.")
        pdf.set_font("Poppins", style='B', size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.cell(200, 5, f"ATT: {att:.2f}", ln=True)

        pdf.cell(200, 5, f"Lift total: {incremental:.2f}", ln=True)
        pdf.cell(200, 5, f"Percentage Lift: {round(mde * 100)}%", ln=True)




        pdf.ln(2)

        pdf.image(temp_image_path, x=10, y=pdf.get_y(), w=190)  


        pdf_output = "reporte.pdf"
        pdf.output(pdf_output, "F")


        os.remove(temp_image_path)


        return pdf_output






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

    #--------------------------------------------------------------------------------------------------------------------------------

st.subheader("1. Upload file")
file = st.file_uploader("Choose a file", type="csv")
if file is not None:
        data = pd.read_csv(file)
        def style_table(df):
            return df.style.set_table_styles([
            {"selector": "thead th", "props": [
                ("font-weight", "bold"),  
                ("color", "black"),   
                ("background-color", "#f0f0f0"),  
                ("font-size", "16px"),    
                ("text-align", "center")  


            ]}
        ]).set_properties(**{'text-align': 'center','white-space': 'nowrap'}).set_table_attributes('class="dataframe"')
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            
            st.markdown(style_table(data.head()).to_html(), unsafe_allow_html=True)
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
        else:
            if 'graph_generated' not in st.session_state:
                st.session_state.graph_generated = False
            if 'current_fig' not in st.session_state:
                st.session_state.current_fig = None
            if col_dates and col_locations and col_target:
                data1 = cleaned_data(data, col_dates=col_dates, col_locations=col_locations, col_target=col_target)

    #--------------------------------------------------------------------------------------------------------------------------------

            st.subheader("2. Data visualization")
            if "graph_button_clicked" not in st.session_state:
                st.session_state.graph_button_clicked = False

            if st.button("Graph data"):
                st.session_state.graph_button_clicked = True  

            if st.session_state.graph_button_clicked:
                fig = plot_geodata(data1)
                st.session_state.fig = fig
                st.plotly_chart(st.session_state.fig)


    #--------------------------------------------------------------------------------------------------------------------------------

            st.subheader("3. Experimental design")
            st.text("Parameter configuration")
            st.markdown("""
            <style>
                .stMultiSelect span[data-baseweb="tag"] {
                    background-color: #aec4e7 !important;
                    color: black !important;
                    border-radius: 5px !important;
                    display: inline-block !important;
                }

                /* Asegurar que los tags tengan un margen y padding adecuado */
                .stMultiSelect span[data-baseweb="tag"] div {
                    color: black !important;
                }
            </style>
            """, unsafe_allow_html=True)
            excluded_locations = st.multiselect("Select excluded locations", data1['location'].unique())
            maximum_treatment_percentage = st.slider("Select maximum_treatment_percentage", 5, 50, 30)
            
            significance_level = st.number_input("Select significance level", min_value=0.01, max_value=0.30, value=0.05, step=0.01)
            if significance_level > 0.2:
                st.warning("A high value could lead to false results")
            st.text("Select range of lifts")
            col1, col2, col3 = st.columns(3)
            with col1:
                delta_min = st.number_input("Lift Min:", min_value=0.01, max_value=0.9, value=0.01, step=0.01)
            with col2:
                delta_max = st.number_input("Lift Max:", min_value=0.02, max_value=1.0, value=0.3, step=0.01)
            with col3:
                delta_step = st.number_input("Lift Step:", min_value=0.01, max_value=1.0, value=0.02, step=0.01)
            if delta_min > delta_max:
                st.error("Lift Min must be less than Lift Max")
            elif delta_min == delta_max:
                st.error("Lift Min and Lift Max must be different")
            elif delta_step == delta_max:
                st.error("Lift Step must be less than Lift Max")
            elif delta_step > delta_max - delta_min:
                st.error("Lift Step must be less than the range of lifts")
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
            elif period_min == period_max:
                st.error("Period Min and Period Max must be different")
            elif period_step == period_max:
                st.error("Period Step must be less than Period Max")
            elif period_step > period_max - period_min:
                st.error("Period Step must be less than the range of periods")  
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
                "maximum_treatment_percentage": maximum_treatment_percentage,
                "significance_level": significance_level,
                "deltas_range": (delta_min, delta_max, delta_step),
                "periods_range": (period_min, period_max+1, period_step),
            }

            
            if current_params != st.session_state.last_params:
                st.session_state.simulation_button_clicked = False  
                st.session_state.selected_point = None  
                st.session_state.last_params = current_params  


            if "simulation_button_clicked" not in st.session_state:
                st.session_state.simulation_button_clicked = False


            if st.button("Run simulation") and not st.session_state.simulation_button_clicked:
                st.session_state.simulation_button_clicked = True  


                progress_bar_1 = st.progress(0)
                status_text_1 = st.empty()
                progress_bar_2 = st.progress(0)
                status_text_2 = st.empty()        

                
                periods, fig1, results = run_geo_analysis_streamlit_app(
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
                st.success('Simulation completed successfully!')
                results_by_size = transform_results_data(results['simulation_results'])
                
                
                
                st.session_state.results = results
                st.session_state.simulation_results = results_by_size
                st.session_state.sensitivity_results = results['sensitivity_results']


                st.session_state.fig1 = plot_mde_results(results_by_size, results['sensitivity_results'], periods)
                #st.write(st.session_state.fig)

                


            if st.session_state.simulation_results is not None:
                st.write('<h4 style="text-align: center;"> Geo Murray MDE Heatmap</h4>', unsafe_allow_html=True)
                fig1 = st.session_state.fig1
                event = st.plotly_chart(fig1,key="heatmap",on_select="rerun")
                #selected_point = plotly_events(fig, click_event=True)



                selected_point = event.selection
                #st.write(selected_point)
                #st.write(selected_point2)
                

   

                if selected_point and "points" in selected_point and len(selected_point["points"]) > 0:
                    point = selected_point["points"][0]



                    if "x" in point and "y" in point:
                        st.session_state.selected_point = point
                        

                if st.session_state.selected_point:
                    x_value, y_value = st.session_state.selected_point["x"], st.session_state.selected_point["y"]

                    try:
                        if isinstance(x_value, str) and "Day-" in x_value:
                            period_idx = int(x_value.replace("Day-", "")) 

                        else:
                            period_idx = None

                        if isinstance(y_value, (int, float)):
                            y_value_str = f"{y_value:.2f}%"

                        else:
                            y_value_str = str(y_value)

                        st.write(f"###### Locations with a holdout of: {y_value_str}")

                        location = None
                        for loc, data in st.session_state.simulation_results.items():

                            holdout_str = f"{data['Holdout Percentage']:.2f}%"
                            if holdout_str == y_value_str:
                                location = loc
                                break

                        if location is None:
                            st.write(f"Error: Location not found for the holdout percentage: {y_value_str}")
                        else:
                            treatment_group = st.session_state.simulation_results.get(location, {}).get('Best Treatment Group', 'N/A')
                            control_group = st.session_state.simulation_results.get(location, {}).get('Control Group', 'N/A')
                            st.write(f"- **Treatment group:** {treatment_group}")
                            st.write(f"- **Control group:** {control_group}")
                            random_sate = data1['location'].unique()[0]
                            filtered_data = data1[data1['location'] == random_sate]
                            firt_day = filtered_data['time'].min()
                            last_day = filtered_data['time'].max()
                            treatment_day = last_day - pd.Timedelta(days=period_idx)
                            last_day = last_day.strftime('%Y-%m-%d')
                            firt_day = firt_day.strftime('%Y-%m-%d')
                            treatment_day = treatment_day.strftime('%Y-%m-%d')
    
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
                                        impact_graph,att,incremental = plot_impact_report(st.session_state.results, period_idx, holdout_percentage)
                                        weights = print_weights(st.session_state.results, round(holdout_percentage, 2))
                                      




                                        

                                        pdf_file = generate_pdf(treatment_group, control_group, holdout_percentage, impact_graph,weights,period_idx,mde,att,incremental,col_target,firt_day,last_day,treatment_day)
                                        
                                        


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
                  




