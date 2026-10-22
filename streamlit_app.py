import streamlit as st

pg = st.navigation(
    {
        "Ferramentas": [
            st.Page("page_1.py", title="CV Fit Score", icon=":material/speed:", default=True),
        ]
    }
)

pg.run()
