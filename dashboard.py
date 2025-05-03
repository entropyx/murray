import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path
from datetime import datetime
import time
import hmac
import os



def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        try:
            secret_password = st.secrets["password"]
        except Exception:
            secret_password = os.environ.get("PASSWORD")
        if hmac.compare_digest(st.session_state["password"], secret_password):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False

    
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    
    if not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    
    return True





if check_password():
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button('Refresh Data'):
            st.rerun()

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


    st.title("Traffic Metrics Dashboard")

    def load_json_data(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get('history', [])
        except Exception as e:
            st.error(f"Error loading JSON file: {e}")
            return None

    col_config1, col_config2 = st.columns(2)


    data_dir = "traffic_metrics"
    json_files = "app_metrics.json"

    try:
        full_path = Path(data_dir) / json_files
        data = load_json_data(full_path)
        
        if data:
            df = pd.DataFrame(data)
            # st.dataframe(df)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df_filtered = df[df['section'].isin(df['section'].unique())]
            
            st.header("Main Metrics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total of events", len(df_filtered))
            with col2:
                st.metric("Unique Sections", df_filtered['section'].nunique())
            with col3:
                st.metric("Days with Activity", df_filtered['date'].nunique())

            st.header("Visualizations")
            col1, col2 = st.columns(2)
            
            with col1:
                section_counts = df_filtered['section'].value_counts()
                fig_sections = px.bar(
                    x=section_counts.index,
                    y=section_counts.values,
                    labels={'x': 'Section', 'y': 'Number of Visits'},
                    title="Distribution of Visits by Section"
                )
                st.plotly_chart(fig_sections, use_container_width=True)
            
            with col2:
                hour_counts = df_filtered['day_of_week'].value_counts().sort_index()
                fig_hours = px.bar(
                    x=hour_counts.index,
                    y=hour_counts.values,
                    labels={'x': 'Day of Week', 'y': 'Number of Visits'},
                    title="Distribution of Visits by Day of Week"
                )
                st.plotly_chart(fig_hours, use_container_width=True)
            
            visits_over_time = df_filtered.groupby('date').size().reset_index(name='visits')
            visits_over_time['date'] = pd.to_datetime(visits_over_time['date'])
            all_dates = pd.date_range(visits_over_time['date'].min(), visits_over_time['date'].max())
            all_dates_df = pd.DataFrame({'date': all_dates})
            visits_filled = all_dates_df.merge(visits_over_time, on='date', how='left').fillna(0)
            visits_filled['visits'] = visits_filled['visits'].astype(int)
            fig_timeline = px.line(
                visits_filled,
                x='date',
                y='visits',
                title="Visits over time"
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            st.header("Detailed Data")
            st.dataframe(df_filtered.tail(5))
            
            
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                label="Download all data (CSV)",
                data=csv,
                file_name="traffic_metrics.csv",
                mime="text/csv"
            )
        else:
            st.warning(f"No JSON files found in the directory '{data_dir}'")
    except Exception as e:
        st.error(f"Error accessing directory: {e}")

    st.markdown("---")

    if time.time() - st.session_state.last_refresh >= 30:  
        st.session_state.last_refresh = time.time()
        time.sleep(1)  
        st.rerun()  