import streamlit as st


Pages = {
    "Murray": [
        st.Page("experimental_design.py", title="Experimental design"),
        st.Page("experimental_evaluation.py", title="Experimental evaluation")
    ]
}

pg = st.navigation(Pages)
pg.run()