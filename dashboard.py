import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path
from datetime import datetime
import time
import hmac
import os
from utils_auth import create_registration_link, validate_registration_link

# Move these functions to the top of the file, after imports
def load_registration_links():
    try:
        if not os.path.exists('traffic_metrics/registration_links.json'):
            return {}
        with open('traffic_metrics/registration_links.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading registration links: {str(e)}")
        return {}

def display_registration_links():
    st.title("Registration Links Management")
    
    # Create new registration link
    with st.expander("Create New Registration Link", expanded=True):
        with st.form("create_link_form"):
            role = st.selectbox("Role", ["user", "admin"])
            max_uses = st.number_input("Maximum Uses", min_value=1, value=1)
            submit = st.form_submit_button("Generate Link")
            
            if submit:
                token = create_registration_link(role=role, max_uses=max_uses)
                if token:
                    base_url = st.query_params.get("base_url", ["https://murray.entropy.tech/"])[0]
                    registration_url = f"{base_url}/?token={token}"
                    st.success("Registration link created successfully!")
                    st.code(registration_url, language="text")


        


# def check_password():
    # """Returns `True` if the user had the correct password."""

    # def password_entered():
    #     """Checks whether a password entered by the user is correct."""
    #     try:
    #         # Intentar obtener la contraseña de secrets.toml
    #         secret_password = st.secrets.get("password")
            
    #         # Si no está en secrets.toml, intentar con variable de entorno
    #         if not secret_password:
    #             secret_password = os.environ.get("PASSWORD")
            
    #         # Verificar que tenemos una contraseña para comparar
    #         if not secret_password:
    #             st.error("No se encontró la contraseña de configuración")
    #             st.session_state["password_correct"] = False
    #             return
            
    #         # Verificar que el usuario ingresó una contraseña
    #         if "password" not in st.session_state or not st.session_state["password"]:
    #             st.error("Por favor ingrese una contraseña")
    #             st.session_state["password_correct"] = False
    #             return
            
    #         # Comparar las contraseñas
    #         if hmac.compare_digest(str(st.session_state["password"]), str(secret_password)):
    #             st.session_state["password_correct"] = True
    #             del st.session_state["password"]  # Limpiar la contraseña de la sesión
    #         else:
    #             st.error("Contraseña incorrecta")
    #             st.session_state["password_correct"] = False
                
    #     except Exception as e:
    #         st.error(f"Error al verificar la contraseña: {str(e)}")
    #         st.session_state["password_correct"] = False

    # # Inicializar el estado de la contraseña
    # if "password_correct" not in st.session_state:
    #     st.session_state["password_correct"] = False

    # # Mostrar el formulario de contraseña si no está autenticado
    # if not st.session_state["password_correct"]:
    #     st.text_input(
    #         "Password", 
    #         type="password", 
    #         on_change=password_entered, 
    #         key="password"
    #     )
    #     return False
    
    # return True





# if check_password(True):
if True:
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

    # Create tabs for different sections
    tab1, tab2 = st.tabs(["Traffic Metrics", "Registration Links"])

    with tab1:
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
                        labels={'x': 'Section', 'y': 'Number of events'},
                        title="Distribution of events by Section"
                    )
                    st.plotly_chart(fig_sections, use_container_width=True)
                
                with col2:
                    hour_counts = df_filtered['day_of_week'].value_counts().sort_index()
                    fig_hours = px.bar(
                        x=hour_counts.index,
                        y=hour_counts.values,
                        labels={'x': 'Day of Week', 'y': 'Number of events'},
                        title="Distribution of events by Day of Week"
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
                    title="Events over time"
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                st.header("Detailed Data")
                st.dataframe(df_filtered.tail(5))
                
                try:
                    csv = df_filtered.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download all data (CSV)",
                        data=csv,
                        file_name="traffic_metrics.csv",
                        mime="text/csv",
                        key="download_csv"
                    )
                except Exception as e:
                    st.error(f"Error to download the data: {str(e)}")
            else:
                st.warning(f"No JSON files found in the directory '{data_dir}'")
        except Exception as e:
            st.error(f"Error accessing directory: {e}")

    with tab2:
        if st.session_state.get('role') != 'admin':
            st.error("Access denied. Admin privileges required.")
        else:
            display_registration_links()

    st.markdown("---")

    if time.time() - st.session_state.last_refresh >= 30:  
        st.session_state.last_refresh = time.time()
        time.sleep(1)  
        st.rerun()  

# Eliminar estas funciones y llamadas que están al final del archivo
# def main():
#     if st.session_state.get('role') != 'admin':
#         st.error("Access denied. Admin privileges required.")
#         return
#     display_registration_links()

# if __name__ == "__main__":
#     main()  