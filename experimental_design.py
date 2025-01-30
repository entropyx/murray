import streamlit as st
import pandas as pd
from Murray.main import *
from Murray.auxiliary import *
from Murray.plots import *



st.title("Geo Murry")

st.subheader("1. Upload file")
file = st.file_uploader("Choose a file", type="csv")
if file is not None:
    data = pd.read_csv(file)
    st.dataframe(data.head())

    st.text("Type the name of columuns the follow parameters:")

    col1, col2, col3 = st.columns(3)

    with col1:
        contains_date = ["date", "day", "time"]
        matching_column1 = next((col for col in data.columns if any(p in col.lower() for p in contains_date)), None)
        col_dates = st.text_input("Dates", matching_column1 if matching_column1 else "")

    with col2:
        contains_locations = ["location", "region", "state"]
        matching_column2 = next((col for col in data.columns if any(q in col.lower() for q in contains_locations)), None)
        col_locations = st.text_input("Locations", matching_column2 if matching_column2 else "")

    with col3:
        col_target = st.text_input("Target")


    if col_dates or col_locations or col_target is not None:
        data1 = cleaned_data(data,col_dates=col_dates,col_locations=col_locations,col_target=col_target)

    st.subheader("2. Data visualization")

    if "graph_button_clicked" not in st.session_state:
        st.session_state.graph_button_clicked = False

    if st.button("Graph data"):
        st.session_state.graph_button_clicked = True  # Store state


    if st.session_state.graph_button_clicked:
        fig = plot_geodata(data1) 
        st.pyplot(fig)

    st.subheader("3. Experimental design")
    st.text("Parameter configiration")

    excluded_states = st.multiselect("Select excluded states", data1['location'].unique())
    minimum_holdout_percentage = st.slider("Select minimum_holdout_percentage",50,95,70)
    significance_level = st.number_input("Select significance level")

    st.text("Select the rage of deltas")
    col1, col2, col3 = st.columns(3)
    with col1:
        delta_min = st.number_input("Delta Min:", min_value=0.0, max_value=1.0, value=0.01, step=0.01)
    with col2:
        delta_max = st.number_input("Delta Max:", min_value=0.0, max_value=1.0, value=0.3, step=0.01)
    with col3:
        delta_step = st.number_input("Delta Step:", min_value=0.001, max_value=1.0, value=0.01, step=0.001)

    deltas_range = (delta_min, delta_max, delta_step)

    st.text("Select range of periods")
    col1, col2, col3 = st.columns(3)
    with col1:
        period_min = st.number_input("Period Min:", min_value=1, max_value=100, value=5, step=1)
    with col2:    
        period_max = st.number_input("Period Max:", min_value=1, max_value=100, value=41, step=1)
    with col3:    
        period_step = st.number_input("Period Step:", min_value=1, max_value=100, value=5, step=1)

    periods_range = (period_min, period_max, period_step)


    st.text("Push botton for start simulation")
    if "simulation_button_clicked" not in st.session_state:
        st.session_state.simulation_button_clicked = False

    if st.button("Run simulation"):
        st.session_state.simulation_button_clicked = True

    if st.session_state.simulation_button_clicked:
        progress_bar_1 = st.progress(0)
        status_text_1 = st.empty()
        progress_bar_2 = st.progress(0)
        status_text_2 = st.empty()
        geo_test = run_geo_analysis(data=data1,
                                    excluded_states=excluded_states,
                                    minimum_holdout_percentage=minimum_holdout_percentage,
                                    significance_level=significance_level,
                                    deltas_range= deltas_range,
                                    periods_range=periods_range,
                                    progress_bar_1=progress_bar_1,
                                    status_text_1=status_text_1,
                                    progress_bar_2=progress_bar_2,
                                    status_text_2=status_text_2)
        



