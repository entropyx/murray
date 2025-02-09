import streamlit as st
from Murray.post_analysis import post_analysis
import pandas as pd
from Murray.auxiliary import cleaned_data
from Murray.plots import *
from fpdf import FPDF
import os
import base64
from streamlit_js_eval import streamlit_js_eval



ENTROPY_LOGO = "utils/Logo Entropy Dark Gray.png"  
MURRAY_LOGO = "utils/Group 105.png"
options = [ENTROPY_LOGO, MURRAY_LOGO]
sidebar_logo = ENTROPY_LOGO
main_body_logo = MURRAY_LOGO



st.logo(sidebar_logo, size="large", icon_image=main_body_logo)


def generate_pdf(treatment_group, control_group, holdout_percentage, impact_graph,percenge_lift,p_value,power,period,permutation_test,treatment_day,firt_day,last_day,col_target,metric_mmm,mmm_option):
        """
        Generates a PDF report with explanations for each aspect.
        """
        
      
        
        impact_graph.set_size_inches(10, 6)   
        temp_image_path_impact = "temp_impact_graph.png"
        impact_graph.savefig(temp_image_path_impact, bbox_inches='tight', dpi=300)  




        permutation_test.set_size_inches(10, 6)   
        temp_image_path_permutation = "temp_permutation_test.png"
        permutation_test.savefig(temp_image_path_permutation, bbox_inches='tight', dpi=300)  
        


        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()


        
        pdf.image("utils/Logo Entropy Dark Gray.png", x=10, y=10, w=20)

        pdf.add_font("Poppins", style="B", fname="utils/Poppins-Bold.ttf", uni=True)
        pdf.add_font("Poppins", "", "utils/Poppins-Regular.ttf", uni=True)

        pdf.set_font("Poppins", style='B', size=20)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 10, "Geo Murray Report", ln=True, align='C')



        
        y_actual = pdf.get_y() + 2
        pdf.line(10, y_actual, 200, y_actual)
        pdf.set_text_color(0, 0, 0)
        
        pdf.ln(7)

        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0,5 , f"This report provides information about the the results of the analysis of a treatment on the variable '{col_target}' with a duration of {period} days. "
                       f"The data included in the design have a period of {firt_day} to {last_day} where the treatment started on {treatment_day} until {last_day}."
                       f"It includes information about the treatment group, control group, and the statistics results of the analysis.")
        

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

        pdf.multi_cell(0, 5, control_group)

        pdf.ln(5)

        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Conversion Percentages")
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)


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
        pdf.cell(200, 10, "Impact Graph", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)


        pdf.multi_cell(0, 5, "The impact graph below shows the causal effects observed in the study. "
                            "It compares the treatment group with the control group over time and demonstrates the cumulative effect of the treatment.")


        pdf.image(temp_image_path_impact, x=10, y=pdf.get_y(), w=180, h=100)  
        os.remove(temp_image_path_impact)


        pdf.add_page()


        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 10, "Metric MMM", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"The {mmm_option} is a important value to evaluate the performance of the treatment. "
                            f"However, it can support calibration of MMM, value is the following")

        pdf.set_font("Poppins", style='B', size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"{mmm_option}: {round(metric_mmm, 2)}")



        pdf.ln(5)

        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 8, "Results statistics", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"Based on the analysis of the injected data and configured parameters, "
                        f"it can be observed that the treatment has the followings results:")

        pdf.set_font("Poppins",style='B', size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"Percentage Lift: {percenge_lift}%")
        pdf.multi_cell(0, 5, f"P-value: {p_value}")
        pdf.multi_cell(0, 5, f"Power: {power}")

                            
        pdf.ln(5)

        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 10, "Permutation Test", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)

        pdf.multi_cell(0, 5, "The permutation test below shows the results of the permutation test. "
                            "It compares the treatment group with the control group over time and demonstrates the cumulative effect of the treatment.")
        
        pdf.ln(5)
        pdf.image(temp_image_path_permutation, x=10, y=pdf.get_y(), w=180, h=100)  
        os.remove(temp_image_path_permutation)







        pdf_output = "reporte.pdf"
        pdf.output(pdf_output, "F")
        return pdf_output
    


st.title("Experimental Evaluation")

# Initialize session state variables
if "graph_generated" not in st.session_state:
        st.session_state.graph_generated = False
if "current_fig" not in st.session_state:
        st.session_state.current_fig = None
if "simulation_button_clicked" not in st.session_state:
        st.session_state.simulation_button_clicked = False
if "evaluation_button_clicked" not in st.session_state:
        st.session_state.evaluation_button_clicked = False
if "pdf_generated" not in st.session_state:
        st.session_state.pdf_generated = False
if "last_params" not in st.session_state:
        st.session_state.last_params = {}
if "permutation_test" not in st.session_state:
        st.session_state.permutation_test = None
if "impact_graph" not in st.session_state:
        st.session_state.impact_graph = None
if "impact_graph_report" not in st.session_state:
        st.session_state.impact_graph_report = None
if "permutation_test_report" not in st.session_state:
        st.session_state.permutation_test_report = None
if "incremental" not in st.session_state:
        st.session_state.incremental = None
if "iROAS" not in st.session_state:
        st.session_state.iROAS = None
if "iCAC" not in st.session_state:
        st.session_state.iCAC = None















st.subheader("1. Upload your data")

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
            # Create a filtered list of columns excluding date and location-like columns
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

            st.subheader("3. Experimental evaluation")
            longitud_data = len(data1['time'].unique())
            #st.write(longitud_data)
            random_sate = data1['location'].unique()[0]
            filtered_data = data1[data1['location'] == random_sate]
            firt_day = filtered_data['time'].min()
            last_day = filtered_data['time'].max()

        


            st.text("Parameter configuration")
            start_treatment = st.date_input("Treatment start date",min_value=firt_day,max_value=last_day,value=firt_day)
            end_treatment = st.date_input("Treatment end date",min_value=firt_day,max_value=last_day,value=last_day)
            treatment_group = st.multiselect("Select treatment group", data1['location'].unique())

            lift = st.number_input("Select lift")

            spend = st.number_input("Select spend")

            mmm_option = st.selectbox("Select the option to calculate the iROAS  iCAC", ["iROAS", "iCAP"])
            st.session_state.mmm_option = mmm_option

            start_treatment = pd.to_datetime(start_treatment)
            end_treatment = pd.to_datetime(end_treatment)

            filtered_data['time'] = pd.to_datetime(filtered_data['time'])
            start_idx = (filtered_data['time'].dt.date == start_treatment.date()).idxmax()
            end_idx = (filtered_data['time'].dt.date == end_treatment.date()).idxmax()


            # Obtener las posiciones relativas
            start_position_treatment = filtered_data.index.get_loc(start_idx)
            end_position_treatment = filtered_data.index.get_loc(end_idx)







            if "evaluation_button_clicked" not in st.session_state:
                st.session_state.evaluation_button_clicked = False

            st.text("Push the button to start the evaluation")
            if "last_params" not in st.session_state:
                st.session_state.last_params = {}

            current_params = {
                "start_treatment": start_treatment,
                "end_treatment": end_treatment,
                "treatment_group": treatment_group,
                "lift": lift
            }

            
            if current_params != st.session_state.last_params:
                st.session_state.evaluation_button_clicked = False
                st.session_state.pdf_generated = False
                if 'pdf_output' in st.session_state:
                    del st.session_state.pdf_output
                st.session_state.last_params = current_params

            if st.button("Evaluate") or st.session_state.evaluation_button_clicked:
                if not st.session_state.evaluation_button_clicked:
                    st.session_state.evaluation_button_clicked = True
                    with st.spinner('Running analysis... Please wait.'):
                        
                        results = post_analysis(data1, start_position_treatment, end_position_treatment, treatment_group, lift)
                        st.session_state.treatment = results[0]
                        st.session_state.counterfactual = results[1]
                        st.session_state.p_value = results[2]
                        st.session_state.power = results[3]
                        st.session_state.percenge_lift = round(results[4], 2)
                        st.session_state.control_group = results[5]
                        st.session_state.conformidad_observada = results[6]
                        st.session_state.conformidades_nulas = results[7]
                        

                        
                        total_Y = data1['Y'].sum()
                        treatment_Y = data1[data1['location'].isin(treatment_group)]['Y'].sum()
                        st.session_state.holdout_percentage = round(((total_Y - treatment_Y) / total_Y) * 100, 2)
                        st.session_state.treatment_group = ", ".join(treatment_group)
                        st.session_state.control_group = ", ".join(st.session_state.control_group)
                        period = end_position_treatment - start_position_treatment
                        st.session_state.permutation_test_report = plot_permutation_test_report(st.session_state.conformidades_nulas,st.session_state.conformidad_observada)
                        st.session_state.period = period
                        


               
                




                        impact_graph,att,incremental = plot_impact_evaluation(
                            st.session_state.counterfactual, 
                            st.session_state.treatment, 
                            st.session_state.period
                        )
                        
                        st.session_state.incremental = incremental
                        
                        st.session_state.impact_graph = impact_graph

                        impact_graph_report,att_report,incremental_report = plot_impact_evaluation_report(
                            st.session_state.counterfactual, 
                            st.session_state.treatment, 
                            st.session_state.period
                        )
                        st.session_state.impact_graph_report = impact_graph_report
                        
                        

                
                if mmm_option == "iROAS":
                    st.session_state.metric_mmm = st.session_state.incremental / spend
                else:
                    st.session_state.metric_mmm = st.session_state.incremental / lift


                

                st.success('Evaluation completed successfully!')
                st.write(f"P-value: {st.session_state.p_value}")
                st.write(f"Power: {st.session_state.power}")
                st.write(f"Percentage Lift: {st.session_state.percenge_lift} %")

                st.write(f"Holdout percentage: {st.session_state.holdout_percentage} %")
                st.write(f"Treatment group: {st.session_state.treatment_group}")
                st.write(f"Control group: {st.session_state.control_group}")

                treatment_day = last_day - pd.Timedelta(days=end_position_treatment - start_position_treatment)
                last_day = end_treatment.strftime('%Y-%m-%d')
                firt_day = firt_day.strftime('%Y-%m-%d')
                treatment_day = treatment_day.strftime('%Y-%m-%d')

                







   
                





                st.write("--------------------------------")
                st.write('<h4 style="text-align: center;"> Graphical representation of the evaluation</h4>', unsafe_allow_html=True)
                st.plotly_chart(st.session_state.impact_graph,use_container_width=True)
                #st.write(st.session_state.permutation_test_report)
                #st.write(st.session_state.impact_graph_report)


                

                st.write("##### Generate report of results")   

                if st.button("Generate and Download PDF", key="pdf_button"):
                    st.session_state.pdf_output = generate_pdf(
                        st.session_state.treatment_group,
                        st.session_state.control_group,
                        st.session_state.holdout_percentage,
                        st.session_state.impact_graph_report,
                        st.session_state.percenge_lift,
                        st.session_state.p_value,
                        st.session_state.power,
                        st.session_state.period,
                        st.session_state.permutation_test_report,
                        treatment_day,
                        firt_day,
                        last_day,
                        col_target,
                        st.session_state.metric_mmm,
                        st.session_state.mmm_option
                    )




                    with open(st.session_state.pdf_output, "rb") as file:
                        b64_pdf = base64.b64encode(file.read()).decode()
                        download_button = f"""
                            var link = document.createElement('a');
                            link.href = 'data:application/pdf;base64,{b64_pdf}';
                            link.download = 'experimental_evaluation_report.pdf';
                            link.click();
                        """
                        streamlit_js_eval(js_expressions=download_button)
                    
                    
                    if os.path.exists(st.session_state.pdf_output):
                        os.remove(st.session_state.pdf_output)

                
            







