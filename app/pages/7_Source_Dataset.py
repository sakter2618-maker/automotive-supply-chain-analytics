"""Analysis of the original public dataset (data/raw/supply_chain_data.csv)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui


@st.cache_data
def load_raw():
    df = pd.read_csv(ui.ROOT / "data" / "raw" / "supply_chain_data.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


df = load_raw()
ui.hero("Source Dataset — Supplier Benchmark",
        "The original 100-SKU supply chain dataset, analyzed with the same questions. "
        "It was also used to calibrate lead times, defect rates and transport modes in the automotive model.",
        tags=["Raw data", "100 SKUs", "5 suppliers"])

g = df.groupby("supplier_name").agg(
    skus=("sku", "count"), avg_defect=("defect_rates", "mean"), avg_lead=("lead_time", "mean"),
    avg_mfg_lead=("manufacturing_lead_time", "mean"), avg_mfg_cost=("manufacturing_costs", "mean"),
    revenue=("revenue_generated", "sum"), production=("production_volumes", "sum"),
    fail_rate=("inspection_results", lambda s: 100 * (s == "Fail").mean())).reset_index()

ui.kpi_row([
    ui.kpi("SKUs", f"{len(df)}", f"{df.product_type.nunique()} product types", ui.BLUE),
    ui.kpi("Avg defect rate", f"{df.defect_rates.mean():.2f}%", "across all SKUs", ui.MAGENTA),
    ui.kpi("Avg supplier lead time", f"{df.lead_time.mean():.1f} d", "range 1–30 days", ui.ORANGE),
    ui.kpi("Inspection fail rate", f"{100 * (df.inspection_results == 'Fail').mean():.0f}%",
           f"{100 * (df.inspection_results == 'Pending').mean():.0f}% still pending", ui.RED),
    ui.kpi("Revenue", ui.fmt_money(df.revenue_generated.sum()), "total generated", ui.GREEN),
])

c1, c2 = st.columns(2)
with c1:
    s = g.sort_values("avg_defect")
    avg = df.defect_rates.mean()
    fig = go.Figure(go.Bar(x=s.avg_defect, y=s.supplier_name, orientation="h",
                           marker_color=[ui.CRITICAL if v == s.avg_defect.max() else ui.NEUTRAL_BAR for v in s.avg_defect],
                           text=[f"{v:.2f}%" for v in s.avg_defect], textposition="outside",
                           hovertemplate="%{y}<br>Avg defect rate %{x:.2f}%<extra></extra>"))
    fig.add_vline(x=avg, line=dict(color=ui.INK_2, dash="dash", width=1), annotation_text=f"avg {avg:.2f}%",
                  annotation_position="top")
    fig.update_xaxes(ticksuffix="%", title="Average defect rate", range=[0, s.avg_defect.max() * 1.3])
    ui.show(ui.style(fig, title="Defect rate by supplier", legend=False))
with c2:
    s = g.sort_values("avg_lead")
    fig = go.Figure(go.Bar(x=s.avg_lead, y=s.supplier_name, orientation="h",
                           marker_color=[ui.SERIOUS if v == s.avg_lead.max() else ui.NEUTRAL_BAR for v in s.avg_lead],
                           text=[f"{v:.1f} d" for v in s.avg_lead], textposition="outside",
                           hovertemplate="%{y}<br>Avg lead time %{x:.1f} days<extra></extra>"))
    fig.update_xaxes(title="Average supplier lead time (days)", range=[0, s.avg_lead.max() * 1.3])
    ui.show(ui.style(fig, title="Lead time by supplier", legend=False))

c1, c2 = st.columns(2)
with c1:
    ct = pd.crosstab(df.supplier_name, df.inspection_results, normalize="index") * 100
    fig = go.Figure()
    for res, color in [("Pass", ui.GOOD), ("Pending", ui.NEUTRAL_BAR), ("Fail", ui.CRITICAL)]:
        if res in ct:
            fig.add_trace(go.Bar(x=ct.index, y=ct[res], name=res, marker_color=color,
                                 marker_line=dict(color="#fff", width=2),
                                 hovertemplate="%{x}<br>" + res + ": %{y:.0f}%<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(ticksuffix="%", title="Share of SKUs", range=[0, 100])
    ui.show(ui.style(fig, title="Inspection results by supplier"))
with c2:
    pt = df.groupby("product_type").agg(defect=("defect_rates", "mean"), cost=("manufacturing_costs", "mean")).reset_index()
    fig = go.Figure(go.Bar(x=pt.product_type, y=pt.defect, marker_color=[ui.BLUE, ui.ORANGE, ui.AQUA][:len(pt)],
                           text=[f"{v:.2f}%" for v in pt.defect], textposition="outside",
                           customdata=pt.cost,
                           hovertemplate="%{x}<br>Defect %{y:.2f}%<br>Mfg cost $%{customdata:.1f}<extra></extra>"))
    fig.update_yaxes(ticksuffix="%", title="Average defect rate", range=[0, pt.defect.max() * 1.3])
    ui.show(ui.style(fig, title="Defect rate by product type", legend=False))

ui.section("Supplier summary (source data)")
st.dataframe(g.round(2), hide_index=True, width="stretch",
             column_config={"supplier_name": "Supplier", "skus": "SKUs", "avg_defect": "Avg defect %",
                            "avg_lead": "Avg lead time (d)", "avg_mfg_lead": "Avg mfg lead time (d)",
                            "avg_mfg_cost": "Avg mfg cost ($)", "revenue": "Revenue ($)",
                            "production": "Production volume", "fail_rate": "Inspection fail %"})
st.caption("Why a second dataset? This file has no dates and no promised-vs-actual delivery, so it cannot measure "
           "on-time delivery or production loss. The automotive dataset (pages 1–6) adds those, using this file's "
           "ranges as a realistic baseline.")
ui.footer()
