"""
Automotive Supply Chain & Quality Analytics — Streamlit dashboard
Run locally:   streamlit run streamlit_app.py
"""

import pandas as pd
import streamlit as st

from app import ui

st.set_page_config(page_title="Automotive Supply Chain & Quality Analytics",
                   page_icon="🚗", layout="wide", initial_sidebar_state="auto")
ui.inject_css()

pages = [
    st.Page("app/pages/1_Executive_Overview.py", title="Executive Overview", icon="📊", default=True),
    st.Page("app/pages/2_Supplier_Delivery.py", title="Supplier Delivery", icon="🚚"),
    st.Page("app/pages/3_Quality_Control.py", title="Quality Control", icon="🔍"),
    st.Page("app/pages/4_Inventory_Production.py", title="Inventory & Production", icon="🏭"),
    st.Page("app/pages/5_Cost_Analysis.py", title="Production Cost", icon="💰"),
    st.Page("app/pages/6_Supplier_Scorecard.py", title="Supplier Scorecard", icon="🏆"),
    st.Page("app/pages/7_Source_Dataset.py", title="Source Dataset", icon="🗂️"),
]
nav = st.navigation(pages)

# ---------------- Global filters (apply to every page) ----------------
full = ui.load()
min_d = full["production_daily"]["date"].min().date()
max_d = full["production_daily"]["date"].max().date()
plants = full["plants"].set_index("plant_id")["plant_name"].to_dict()

with st.sidebar:
    st.markdown("### Filters")
    rng = st.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    if isinstance(rng, (tuple, list)) and len(rng) == 2:
        start, end = rng
    else:  # user has picked only the first date so far
        start, end = min_d, max_d
    sel_plants = st.multiselect("Plant", options=list(plants), format_func=lambda k: plants[k],
                                placeholder="All plants")
    sel_regions = st.multiselect("Supplier region", options=["Domestic", "Nearshore", "Overseas"],
                                 placeholder="All regions")
    st.caption("Filters apply to every page. Leave a box empty to include everything.")
    st.divider()
    st.caption("Built with Python · pandas · Plotly · Streamlit · PostgreSQL")

st.session_state["filters"] = dict(start=pd.Timestamp(start), end=pd.Timestamp(end),
                                   plants=sel_plants, regions=sel_regions)

nav.run()
