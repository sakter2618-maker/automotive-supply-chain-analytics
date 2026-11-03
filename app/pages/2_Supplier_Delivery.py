import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

d = ui.data()
po = d["purchase_orders"]

ui.hero("Supplier Delivery Performance & Supply Chain Delays",
        "Which suppliers miss promised dates, by how much, and why.",
        tags=["Delivery", "OTD vs 95% target", "Root causes"])
if ui.empty_guard(po):
    st.stop()

dl = m.supplier_delivery(po)
k = m.headline_kpis(d)
reasons = m.delay_reasons(po)
ui.kpi_row([
    ui.kpi("Deliveries", f"{k['deliveries']:,}", "purchase-order lots", ui.BLUE),
    ui.kpi("On-time delivery", f"{k['otd_pct']:.1f}%", "target 95%", ui.AQUA,
           "good" if k["otd_pct"] >= 95 else ("warn" if k["otd_pct"] >= 90 else "bad")),
    ui.kpi("Late lots", f"{k['late_deliveries']:,}", f"avg {k['avg_days_late']:.1f} days late", ui.ORANGE),
    ui.kpi("Suppliers below target", f"{(dl.otd_pct < 95).sum()} of {len(dl)}", "OTD < 95%", ui.RED),
    ui.kpi("Top delay cause", reasons.iloc[0].delay_reason if len(reasons) else "—",
           f"{reasons.iloc[0].share_pct:.0f}% of late lots" if len(reasons) else "", ui.YELLOW),
    ui.kpi("Expedited air freight", ui.fmt_money(k["expedite_cost"]), f"{int(po.expedited_flag.sum())} lots flown in", ui.VIOLET),
])

left, right = st.columns([1, 1])
with left:
    s = dl.sort_values("otd_pct")
    colors = [ui.GOOD if v >= 95 else (ui.WARNING if v >= 90 else ui.CRITICAL) for v in s.otd_pct]
    fig = go.Figure(go.Bar(x=s.otd_pct, y=s.supplier_name, orientation="h", marker_color=colors,
                           text=[f"{v:.1f}%" for v in s.otd_pct], textposition="outside",
                           customdata=s[["avg_days_late", "deliveries"]],
                           hovertemplate="<b>%{y}</b><br>OTD %{x:.1f}%<br>Avg %{customdata[0]:.1f} days late"
                                         "<br>%{customdata[1]} lots<extra></extra>"))
    fig.add_vline(x=95, line=dict(color=ui.INK_2, dash="dash", width=1),
                  annotation_text="95%", annotation_position="top")
    fig.update_xaxes(range=[0, 112], ticksuffix="%", title="On-time delivery %", tickvals=[0, 25, 50, 75, 100])
    ui.show(ui.style(fig, height=380, title="On-time delivery by supplier (green ≥95 · amber ≥90 · red <90)", legend=False))
with right:
    b = m.delay_buckets(po)
    order = dl.sort_values("otd_pct").supplier_name.tolist()
    fig = go.Figure()
    for bucket, color in zip(["On time", "1-2 days late", "3-5 days late", ">5 days late"],
                             [ui.NEUTRAL_BAR, ui.YELLOW, ui.ORANGE, ui.RED]):
        g = b[b.bucket == bucket].set_index("supplier_name").reindex(order)
        fig.add_trace(go.Bar(x=g.share_pct, y=order, orientation="h", name=bucket, marker_color=color,
                             marker_line=dict(color="#fff", width=2),
                             hovertemplate="%{y}<br>" + bucket + ": %{x:.1f}%<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(ticksuffix="%", range=[0, 100], title="Share of lots")
    ui.show(ui.style(fig, height=380, title="Delay severity mix by supplier"))

# Heatmap: supplier x month
ui.section("When did deliveries slip?", "Monthly on-time delivery % per supplier — darker red = worse.")
mo = m.monthly_otd(po, by="supplier_name")
piv = mo.pivot(index="supplier_name", columns="month", values="otd_pct").reindex(order[::-1])
fig = go.Figure(go.Heatmap(
    z=piv.values, x=[c.strftime("%b %y") for c in piv.columns], y=piv.index,
    colorscale=[[0, "#b3261e"], [0.45, "#ec835a"], [0.7, "#f0efec"], [1, "#2a78d6"]], zmin=30, zmax=100,
    xgap=2, ygap=2, colorbar=dict(title="OTD %", ticksuffix="%", thickness=12),
    hovertemplate="%{y}<br>%{x}: %{z:.1f}% on time<extra></extra>"))
ui.show(ui.style(fig, height=380, legend=False))

left, right = st.columns(2)
with left:
    r = reasons.sort_values("late_deliveries")
    fig = go.Figure(go.Bar(x=r.late_deliveries, y=r.delay_reason, orientation="h", marker_color=ui.ORANGE,
                           text=[f"{v:.0f}%" for v in r.share_pct], textposition="outside",
                           customdata=r[["avg_days_late", "total_days_late"]],
                           hovertemplate="<b>%{y}</b><br>%{x} late lots<br>Avg %{customdata[0]:.1f} days late"
                                         "<br>%{customdata[1]:,} total days late<extra></extra>"))
    fig.update_xaxes(title="Late deliveries", range=[0, r.late_deliveries.max() * 1.18])
    ui.show(ui.style(fig, title="Root causes of late deliveries", legend=False))
with right:
    reg = (po.groupby("region").agg(otd=("on_time_flag", "mean"), lead=("lead_time_days", "mean"),
                                    lots=("po_id", "count")).reset_index())
    reg["otd"] *= 100
    reg = reg.sort_values("otd", ascending=False)
    fig = go.Figure(go.Bar(x=reg.region, y=reg.otd, marker_color=[ui.REGION_COLORS[x] for x in reg.region],
                           text=[f"{v:.1f}%<br>{l:.0f}-day lead" for v, l in zip(reg.otd, reg.lead)],
                           textposition="outside",
                           hovertemplate="%{x}<br>OTD %{y:.1f}%<extra></extra>"))
    fig.update_yaxes(range=[0, 115], ticksuffix="%", title="On-time delivery %")
    ui.show(ui.style(fig, title="Domestic vs nearshore vs overseas", legend=False))

ui.section("Supplier delivery table")
tbl = dl[["supplier_name", "region", "deliveries", "otd_pct", "gap_to_target", "avg_days_late", "worst_delay", "expedited"]]
st.dataframe(
    tbl, hide_index=True, width="stretch",
    column_config={
        "supplier_name": "Supplier", "region": "Region", "deliveries": "Lots",
        "otd_pct": st.column_config.ProgressColumn("On-time %", format="%.1f%%", min_value=0, max_value=100),
        "gap_to_target": st.column_config.NumberColumn("Gap to 95% (pts)", format="%.1f"),
        "avg_days_late": st.column_config.NumberColumn("Avg days late", format="%.1f"),
        "worst_delay": st.column_config.NumberColumn("Worst delay (days)"),
        "expedited": st.column_config.NumberColumn("Expedited lots"),
    })
ui.footer()
