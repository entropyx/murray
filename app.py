import streamlit as st






# Configure page
st.set_page_config(
    page_title="Geo Murray",
    page_icon="utils/Group 105.png",
    layout="wide"
)


# Navigation setup
Pages = {
    "Murray": [
        st.Page("experimental_design.py", title="Experimental design"),
        st.Page("experimental_evaluation.py", title="Experimental evaluation")
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
    /* Forzar Inter en headers y subheaders */
    h1, h2, h3, h4, h5, h6, .stTextHeader {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
    }
    /* Aplicar Inter a elementos interactivos */
    button, input, textarea, select {
        font-family: 'Inter', sans-serif !important;
    }

    /* Ajustar tamaño y peso de fuente en botones */
    .stButton>button {
        font-size: 16px;
        font-weight: 600;
    }

    /* Ajustar fuente en inputs de texto */
    .stTextInput>div>div>input, 
    .stTextArea>div>textarea, 
    .stSelectbox>div>div>select, 
    .stMultiselect>div>div>div {
        font-family: 'Inter', sans-serif !important;
    }

    /* Ajustar fuente en sliders */
    .stSlider {
        font-family: 'Inter', sans-serif;
    }
    
    </style>
    """,
    unsafe_allow_html=True
)