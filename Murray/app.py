import os
import streamlit as st


st.set_page_config(
    page_title="Geo Murray",
    page_icon="utils/Group 105.png",
    layout="wide"
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