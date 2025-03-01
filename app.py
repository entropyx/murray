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