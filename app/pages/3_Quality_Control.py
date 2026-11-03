import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

d = ui.data()
qi = d["quality_inspections"]

ui.hero("Quality Control & Defect Rate",
        "Incoming inspection results, defect rates by component and supplier, Pareto of causes and SPC control chart.",
        tags=["Quality", "PPM", "p-chart (SPC)"])
if ui.empty_guard(qi):
    st.stop()

k = m.headline_kpis(d)
cq = m.component_quality(qi)
sq = m.supplier_quality(qi)
ui.kpi_row([
    ui.kpi("Parts inspected", f"{qi.sample_size.sum():,}", f"{len(qi):,} lots", ui.BLUE),
    ui.kpi("Defect rate", f"{k['defect_rate_pct']:.2f}%", f"{k['ppm']:,.0f} PPM", ui.MAGENTA,
           "good" if k["ppm"] <= 5000 else ("warn" if k["ppm"] <= 8000 else "bad")),
    ui.kpi("First-pass yield", f"{k['first_pass_yield_pct']:.1f}%", "lots passed first time", ui.AQUA),
    ui.kpi("Failed lots", f"{k['failed_lots']}", f"{(qi.inspection_result == 'Conditional').sum()} conditional", ui.RED),
    ui.kpi("Worst component", cq.iloc[0].component_name, f"{cq.iloc[0].defect_rate_pct:.2f}% defective", ui.ORANGE),
    ui.kpi("Rework cost", ui.fmt_money(k["rework_cost"]), "sorting + rework", ui.VIOLET),
])

left, right = st.columns([1, 1])
with left:
    top = cq.head(10).sort_values("defect_rate_pct")
    avg = k["defect_rate_pct"]
    colors = [ui.CRITICAL if v > 2 * avg else (ui.SERIOUS if v > avg else ui.NEUTRAL_BAR) for v in top.defect_rate_pct]
    fig = go.Figure(go.Bar(x=top.defect_rate_pct, y=top.component_name, orientation="h", marker_color=colors,
                           text=[f"{v:.2f}%" for v in top.defect_rate_pct], textposition="outside",
                           customdata=top[["supplier_name", "ppm", "failed_lots"]],
                           hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>%{x:.2f}% · %{customdata[1]:,.0f} PPM"
                                         "<br>%{customdata[2]} failed lots<extra></extra>"))
    fig.add_vline(x=avg, line=dict(color=ui.INK_2, dash="dash", width=1),
                  annotation_text=f"avg {avg:.2f}%", annotation_position="top")
    fig.update_xaxes(ticksuffix="%", title="Defect rate %", range=[0, top.defect_rate_pct.max() * 1.25])
    ui.show(ui.style(fig, height=400, title="Top 10 components by defect rate (red = 2× average)", legend=False))
with right:
    s = sq.sort_values("first_pass_yield_pct", ascending=False)
    fig = go.Figure()
    for res, col in [("passed", "Pass"), ("conditional", "Conditional"), ("failed", "Fail")]:
        fig.add_trace(go.Bar(x=s.supplier_name, y=100 * s[res] / s.lots, name=col,
                             marker_color=ui.RESULT_COLORS[col], marker_line=dict(color="#fff", width=2),
                             hovertemplate="%{x}<br>" + col + ": %{y:.1f}% of lots<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(ticksuffix="%", title="Share of inspected lots", range=[0, 100])
    fig.update_xaxes(tickangle=-30)
    ui.show(ui.style(fig, height=400, title="Inspection results by supplier"))

left, right = st.columns([1, 1])
with left:
    pa = m.defect_pareto(qi)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=pa.primary_defect_type, y=pa.share_pct, name="Share of defects",
                         marker_color=ui.MAGENTA,
                         hovertemplate="%{x}<br>%{y:.1f}% of defects<extra></extra>"))
    fig.add_trace(go.Scatter(x=pa.primary_defect_type, y=pa.cumulative_pct, name="Cumulative %",
                             mode="lines+markers", line=dict(color=ui.INK_2, width=2), marker=dict(size=7),
                             hovertemplate="%{x}<br>Cumulative %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=80, line=dict(color=ui.MUTED, dash="dot", width=1), annotation_text="80%",
                  annotation_position="top left")
    fig.update_yaxes(ticksuffix="%", range=[0, 105], title="% of all defects")
    fig.update_xaxes(tickangle=-40)
    ui.show(ui.style(fig, height=420, title="Pareto of defect types (80/20 rule)"))
with right:
    comps = cq.sort_values("defect_rate_pct", ascending=False)
    choice = st.selectbox("Component for the control chart", comps.component_id,
                          format_func=lambda c: comps.set_index("component_id").loc[c, "component_name"])
    pc = m.p_chart(qi, choice)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pc.month, y=pc.ucl_pct, name="Upper control limit", mode="lines",
                             line=dict(color=ui.CRITICAL, width=1.5, dash="dash"),
                             hovertemplate="UCL %{y:.2f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=pc.month, y=pc.center_pct, name="Average", mode="lines",
                             line=dict(color=ui.MUTED, width=1.5), hovertemplate="Avg %{y:.2f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=pc.month, y=pc.defect_rate_pct, name="Monthly defect %", mode="lines+markers",
                             line=dict(color=ui.BLUE, width=2),
                             marker=dict(size=9, color=[ui.CRITICAL if o else ui.BLUE for o in pc.out_of_control],
                                         line=dict(color="#fff", width=2)),
                             hovertemplate="%{x|%b %Y}<br>%{y:.2f}% defective<extra></extra>"))
    fig.update_yaxes(ticksuffix="%", title="Defect rate %", rangemode="tozero")
    n_out = int(pc.out_of_control.sum())
    ui.show(ui.style(fig, height=350, title=f"p-chart: {n_out} month(s) out of control (red points)"))

ui.section("Component quality table")
st.dataframe(
    cq[["component_name", "category", "supplier_name", "inspected", "defects", "defect_rate_pct", "ppm",
        "failed_lots", "rework_cost"]],
    hide_index=True, width="stretch",
    column_config={
        "component_name": "Component", "category": "Category", "supplier_name": "Supplier",
        "inspected": st.column_config.NumberColumn("Inspected", format="%d"),
        "defects": st.column_config.NumberColumn("Defects", format="%d"),
        "defect_rate_pct": st.column_config.ProgressColumn("Defect %", format="%.2f%%", min_value=0,
                                                           max_value=float(max(cq.defect_rate_pct.max(), 1))),
        "ppm": st.column_config.NumberColumn("PPM", format="%.0f"),
        "failed_lots": "Failed lots",
        "rework_cost": st.column_config.NumberColumn("Rework cost ($)", format="%.0f"),
    })
ui.footer()
