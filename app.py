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
