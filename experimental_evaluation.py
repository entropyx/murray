import streamlit as st
from Murray.post_analysis import run_geo_evaluation
import pandas as pd
from Murray.auxiliary import cleaned_data
from Murray.plots import *
from fpdf import FPDF
import os
import base64
from streamlit_js_eval import streamlit_js_eval
from Murray.metrics import update_metrics, load_metrics



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



st.logo(sidebar_logo, size="large", icon_image=main_body_logo)


def generate_pdf(treatment_group, control_group, holdout_percentage, 
                 impact_graph,percenge_lift,p_value,power,period,
                 permutation_test,treatment_day,firt_day,last_day,
                 col_target,metric_mmm,mmm_option,lift_total,firt_report_day,second_report_day,
                 pre_treatment,pre_counterfactual,post_treatment,post_counterfactual,att,incremental,df,spend):
        """
        Generates a PDF report with explanations for each aspect.
        """
        
      
        
        impact_graph.set_size_inches(10, 6)   
        temp_image_path_impact = "temp_impact_graph.png"
        impact_graph.savefig(temp_image_path_impact, bbox_inches='tight', dpi=300)  




        permutation_test.set_size_inches(10, 6)   
        temp_image_path_permutation = "temp_permutation_test.png"
        permutation_test.savefig(temp_image_path_permutation, bbox_inches='tight', dpi=300)  
        

        header_bg = (103, 85, 130)  
        alt_row_bg = (209, 204, 217)  
        white_row_bg = (246, 246, 246)  
        text_color = (33, 31, 36)
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
                       f"The data included in the design have a period of {firt_day} to {last_day} where the treatment started on {firt_day} until {last_day}."
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
        pdf.cell(200, 10, "Incrementality and statistical results.", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"Based on the analysis of the injected data and configured parameters, "
                        f"it can be observed that the treatment has the followings results:")

        pdf.set_font("Poppins",style='B', size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"Percentage Lift: {percenge_lift}%")
        pdf.multi_cell(0, 5, f"Lift total: {lift_total}")
        pdf.multi_cell(0, 5, f"P-value: {p_value}")
        pdf.multi_cell(0, 5, f"Power: {power}")

        pdf.ln(4)
        
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"It is important to be able to identify the impact of the intervention pre-intervention and" 
                       f"post-intervention in real values. In this case, a small table is presented where the pre-intervention"
                       f"value (with the same duration as the treatment period) and the post-intervention value are observed."
                       f"This allows for a quick and simple identification of the impact that an intervention would have in"
                       f"comparison to the locations where it is not applied (counterfactual).")

        pdf.ln(2)
        if pdf.get_y() > 240:
            pdf.add_page() 

        col_widths = [62.5, 42.5, 42.5, 42.5]
        row_height = 8

        
        header_texts = [
            "Group",
            f"Pre-treatment\n({firt_report_day} to {second_report_day})",
            f"Post-treatment\n({firt_day} to {last_day})",
            "Increment"
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
        row_height = 8  
        header_bg = (103, 85, 130)  
        alt_row_bg = (209, 204, 217)  
        white_row_bg = (246, 246, 246)  
        text_color = (33, 31, 36)

        
        pdf.set_text_color(*text_color)
        pdf.set_font("Poppins", "", 10)
        y_data_start = pdf.get_y()

        for i, row in df.iterrows():
            bg_color = alt_row_bg if i % 2 else white_row_bg
            pdf.set_fill_color(*bg_color)
            
            pdf.cell(col_widths[0], row_height, str(row["Group"]), border=1, ln=0, align='C', fill=True)
            pdf.cell(col_widths[1], row_height, f"{row['Pre-treatment']:,.2f}", border=1, ln=0, align='C', fill=True)
            pdf.cell(col_widths[2], row_height, f"{row['Post-treatment']:,.2f}", border=1, ln=1, align='C', fill=True)

        y_data_end = pdf.get_y()
        altura_total = y_data_end - y_data_start

        
        x_fourth_col = x_start + col_widths[0] + col_widths[1] + col_widths[2]
        pdf.set_xy(x_fourth_col, y_data_start)

        pdf.set_text_color(*text_color)
        pdf.set_font("Poppins", "B", 10)
        pdf.cell(col_widths[3], altura_total, f"{percenge_lift}%", border=1, ln=1, align='C', fill=True)

        
        pdf.ln(5)
        if pdf.get_y() > 250:
            pdf.add_page() 

        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        increment = np.sum(post_treatment)- np.sum(post_counterfactual)
        
        pdf.multi_cell(0, 5, f"The permutation test below shows the results of the permutation test. "
                            f"It compares the treatment group with the control group over time and demonstrates the cumulative effect of the treatment." 
                            f"In this case, the metric observed in the graph, called Observed difference, represents the value of the difference (increase "
                            f"or decrease) observed in the previous table. This value is {round(increment,2):,.2f}, and the graph visually indicates whether it falls"
                            f" within the significance zone, allowing us to conclude whether the result is statistically significant.")
            
        pdf.image(temp_image_path_permutation, x=10, y=pdf.get_y(), w=180, h=100)  
        
        pdf.set_y(pdf.get_y() + 105)  
        os.remove(temp_image_path_permutation)
        
        pdf.ln(5)
        if pdf.get_y() > 250:
            pdf.add_page() 

        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, "The impact graph below shows the causal effects observed in the study. "
                            "It compares the treatment group with the control group over time and demonstrates the cumulative effect of the treatment.")

        pdf.ln(5)
        if pdf.get_y() > 250:
            pdf.add_page() 

        pdf.image(temp_image_path_impact, x=10, y=pdf.get_y(), w=180, h=100)  
        os.remove(temp_image_path_impact)
        
        
        pdf.set_y(pdf.get_y() + 105) 
        pdf.add_page()

        pdf.set_font("Poppins", style='B', size=12)
        pdf.set_text_color(27, 0, 67)
        pdf.cell(200, 10, "Incremental Performance Evaluation", ln=True)
        pdf.set_font("Poppins", size=10)
        pdf.set_text_color(33, 31, 36)
        pdf.multi_cell(0, 5, f"The {mmm_option} is a important value to evaluate the performance of the treatment which calculate the {mmm_option} based on the spend and the incremental. "
                            f"However, it can support calibration of MMM, value is the following")


        pdf.ln(1.5)
        
        col_widths = [60, 60, 60]
        row_height = 8

        header_texts = ["Spend", "Incremental", mmm_option]
        
        x_start = pdf.get_x()
        y_start = pdf.get_y() + 5  

        pdf.set_fill_color(*header_bg)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Poppins", "B", 10)

        for i, txt in enumerate(header_texts):
            pdf.cell(col_widths[i], row_height, txt, border=1, ln=0, align='C', fill=True)
        pdf.ln(row_height)

        pdf.set_text_color(*text_color)
        pdf.set_font("Poppins", "", 10)
        pdf.set_fill_color(*white_row_bg)
        
        pdf.cell(col_widths[0], row_height, f"${spend:,.2f}", border=1, ln=0, align='C', fill=True)
        pdf.cell(col_widths[1], row_height, f"${incremental:,.2f}", border=1, ln=0, align='C', fill=True)
        pdf.cell(col_widths[2], row_height, f"${round(metric_mmm, 2):,.2f}", border=1, ln=1, align='C', fill=True)

        pdf.ln(5)  




        pdf_output = "reporte.pdf"
        pdf.output(pdf_output, "F")
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
if 'lift_total' not in st.session_state:
     st.session_state.lift_total = None
if 'pre_treatment' not in st.session_state:
        st.session_state.pre_treatment = None
if 'pre_counterfactual' not in st.session_state:
        st.session_state.pre_counterfactual = None
if 'post_treatment' not in st.session_state:
        st.session_state.post_treatment = None
if 'post_counterfactual' not in st.session_state:
        st.session_state.post_counterfactual = None
if 'att_report' not in st.session_state:
        st.session_state.att_report = None
if 'incremental_report' not in st.session_state:
        st.session_state.incremental_report = None
if 'last_day' not in st.session_state:
        st.session_state.last_day = None
if 'firt_day' not in st.session_state:
        st.session_state.firt_day = None
if 'firt_report_day' not in st.session_state:
        st.session_state.firt_report_day = None
if 'second_report_day' not in st.session_state:
        st.session_state.second_report_day = None
        













st.subheader("1. Upload your data")

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
            
            st.subheader("3. Experimental evaluation")
            random_sate = data1['location'].unique()[0]
            filtered_data = data1[data1['location'] == random_sate]
            firt_day = filtered_data['time'].min()
            last_day = filtered_data['time'].max()
            

        


            st.text("Parameter configuration")
            start_treatment = st.date_input("Treatment start date",min_value=firt_day,max_value=last_day,value=firt_day)
            end_treatment = st.date_input("Treatment end date",min_value=firt_day,max_value=last_day,value=last_day)
            treatment_group = st.multiselect("Select treatment group", data1['location'].unique())
            spend = st.number_input("Select spend")
            mmm_option = st.selectbox("Select the option to calculate the iROAS or iCPA", ["iROAS", "iCPA"])
            
            st.session_state.mmm_option = mmm_option
            start_treatment = pd.to_datetime(start_treatment)
            end_treatment = pd.to_datetime(end_treatment)

            filtered_data['time'] = pd.to_datetime(filtered_data['time'])
            start_idx = (filtered_data['time'].dt.date == start_treatment.date()).idxmax()
            end_idx = (filtered_data['time'].dt.date == end_treatment.date()).idxmax()

            
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
                "spend": spend,
                "mmm_option": mmm_option,
                'col_target': col_target
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
                    
                    update_metrics("experimental_evaluation")
                    
                    with st.spinner('Running analysis... Please wait.'):
                        
                        results = run_geo_evaluation(data1, start_treatment, end_treatment, treatment_group, spend)
                        treatment = results['treatment']
                        st.session_state.treatment = treatment
                        counterfactual = results['predictions']
                        st.session_state.counterfactual = counterfactual
                        p_value = results['p_value']
                        st.session_state.p_value = p_value
                        power = results['power']
                        st.session_state.power = power
                        percenge_lift = round(results['percenge_lift'], 2)
                        st.session_state.percenge_lift = percenge_lift
                        control_group = results['control_group']
                        st.session_state.control_group = control_group
                        observed_stat = results['observed_stat']
                        st.session_state.observed_stat = observed_stat
                        null_stats = results['null_stats']
                        st.session_state.null_stats = null_stats
                        
                        


                        
                        total_Y = data1['Y'].sum()
                        treatment_Y = data1[data1['location'].isin(treatment_group)]['Y'].sum()
                        lift_total_pre = results["treatment"] - results["predictions"]
                        lift_total = np.sum(lift_total_pre[start_position_treatment:])
                        st.session_state.lift_total = round(lift_total,2)
                        st.session_state.holdout_percentage = round(((total_Y - treatment_Y) / total_Y) * 100, 2)
                        st.session_state.treatment_group = ", ".join(treatment_group)
                        st.session_state.control_group = ", ".join(st.session_state.control_group)

                        period = end_position_treatment - start_position_treatment+1
                        st.session_state.permutation_test_report = plot_permutation_test_report(results)
                        st.session_state.period = period
                        second_report_day = last_day - pd.Timedelta(days=period)
                        firt_report_day = last_day - pd.Timedelta(days=(period*2)-1)
                        treatment_day = last_day - pd.Timedelta(days=period-1)
                
                        
                        


               
                


                        
                        length_treatment = len(treatment_group)
                        impact_graph,att,incremental = plot_impact_evaluation_streamlit(results,filtered_data,length_treatment)
                        st.session_state.incremental = incremental
                        
                        st.session_state.impact_graph = impact_graph

                        impact_graph_report,pre_treatment,pre_counterfactual,post_treatment,post_counterfactual,att_report,incremental_report = plot_impact_evaluation_report(results)
                        st.session_state.impact_graph_report = impact_graph_report
                        st.session_state.pre_treatment = pre_treatment
                        st.session_state.pre_counterfactual = pre_counterfactual
                        st.session_state.post_treatment = post_treatment
                        st.session_state.post_counterfactual = post_counterfactual
                        st.session_state.att_report = att_report
                        st.session_state.incremental_report = incremental_report

                        
                        
                        

                
                if mmm_option == "iROAS":
                    st.session_state.metric_mmm = spend / st.session_state.incremental 
                else:
                    st.session_state.metric_mmm = spend / st.session_state.incremental 


                

                st.success('Evaluation completed successfully!')
                st.write(f"P-value: {st.session_state.p_value}")
                st.write(f"Power: {st.session_state.power}")
                st.write(f"Percentage Lift: {st.session_state.percenge_lift} %")
                st.write(f"Lift_total: {st.session_state.lift_total}")
                st.write(f"Holdout percentage: {st.session_state.holdout_percentage} %")
                st.write(f"Treatment group: {st.session_state.treatment_group}")
                st.write(f"Control group: {st.session_state.control_group}")
           
                
 
                
                last_day = pd.to_datetime(last_day)
                treatment_day = last_day - pd.Timedelta(days=end_position_treatment - start_position_treatment)
                second_report_day = last_day - pd.Timedelta(days=st.session_state.period)
                firt_report_day = last_day - pd.Timedelta(days=(st.session_state.period*2)-1)
                treatment_day = last_day - pd.Timedelta(days=st.session_state.period-1)
                last_day = last_day.strftime('%Y-%m-%d')
                firt_day = firt_day.strftime('%Y-%m-%d')
                firt_report_day = firt_report_day.strftime('%Y-%m-%d')
                second_report_day = second_report_day.strftime('%Y-%m-%d')



                 # Absolute values (comoarison)
                pre_treatment = st.session_state.pre_treatment
                pre_counterfactual = st.session_state.pre_counterfactual
                post_treatment = st.session_state.post_treatment
                post_counterfactual = st.session_state.post_counterfactual

                df = pd.DataFrame(
                                            {
                                                "Group": ["Treatment", "Counterfactual (control)", "Absolute difference"],
                                                "Pre-treatment": [np.sum(pre_treatment),np.sum(pre_counterfactual), np.abs(np.sum(pre_treatment)-np.sum(pre_counterfactual))],
                                                "Post-treatment": [np.sum(post_treatment), np.sum(post_counterfactual),np.abs(np.sum(post_treatment)- np.sum(post_counterfactual))],
                                                "Increment": [" " ," " ," " ]
                                                
                                            }
                                        )
                







   
                





                st.write("--------------------------------")
                st.write('<h4 style="text-align: center;"> Graphical representation of the evaluation</h4>', unsafe_allow_html=True)
                st.plotly_chart(st.session_state.impact_graph,use_container_width=True)
                


                

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
                        st.session_state.mmm_option,
                        st.session_state.lift_total,
                        firt_report_day,
                        second_report_day,
                        st.session_state.pre_treatment,
                        st.session_state.pre_counterfactual,
                        st.session_state.post_treatment,
                        st.session_state.post_counterfactual,
                        st.session_state.att_report,
                        st.session_state.incremental_report,
                        df,
                        spend
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

                
            













