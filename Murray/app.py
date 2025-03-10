import os
import streamlit as st
import toml

st.set_page_config(
    page_title="Geo Murray",
    page_icon="utils/Group 105.png",
    layout="wide"
)




# Obtener la ruta del paquete instalado
package_root = os.path.dirname(__file__)

# Ruta del config.toml dentro del paquete
config_path = os.path.join(package_root, ".streamlit", "config.toml")

# Verificar si el archivo existe antes de cargarlo
if not os.path.exists(config_path):
    st.error(f"Error: No se encontró {config_path}")
else:
    config = toml.load(config_path)
    ui_colors = config.get("theme", {})

    primaryColor = ui_colors.get("primaryColor", "#8bb0d0")
    backgroundColor = ui_colors.get("backgroundColor", "#F3F5F7")
    secondaryBackgroundColor = ui_colors.get("secondaryBackgroundColor", "#8BB0D0")
    textColor = ui_colors.get("textColor", "#000000")

    # Aplicar los estilos manualmente con CSS en Streamlit
    st.markdown(
        f"""
        <style>
            body {{
                background-color: {backgroundColor};
                color: {textColor};
            }}
            .stApp {{
                background-color: {secondaryBackgroundColor};
            }}
            .stButton>button {{
                background-color: {primaryColor} !important;
                color: {textColor} !important;
            }}
        </style>
        """,
        unsafe_allow_html=True
    )


package_root = os.path.dirname(__file__)


design_path = os.path.join(package_root, "experimental_design.py")
evaluation_path = os.path.join(package_root, "experimental_evaluation.py")


if not os.path.exists(design_path):
    st.error(f"Error: No se encontró {design_path}")
if not os.path.exists(evaluation_path):
    st.error(f"Error: No se encontró {evaluation_path}")


Pages = {
    "Murray": [
        st.Page(design_path, title="Experimental Design"),
        st.Page(evaluation_path, title="Experimental Evaluation")
    ]
}

pg = st.navigation(Pages)
pg.run()



st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6, .stTextHeader {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
    }
    
    button, input, textarea, select {
        font-family: 'Inter', sans-serif !important;
    }

    
    .stButton>button {
        font-size: 16px;
        font-weight: 600;
    }

    
    .stTextInput>div>div>input, 
    .stTextArea>div>textarea, 
    .stSelectbox>div>div>select, 
    .stMultiselect>div>div>div {
        font-family: 'Inter', sans-serif !important;
    }

    
    .stSlider {
        font-family: 'Inter', sans-serif;
    }
    
    </style>
    """,
    unsafe_allow_html=True
)