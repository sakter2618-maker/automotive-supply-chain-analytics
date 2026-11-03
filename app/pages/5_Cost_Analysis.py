import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

d = ui.data()
po, qi, pr = d["purchase_orders"], d["quality_inspections"], d["production_daily"]

ui.hero("Production Cost Analysis",
        "Where production money goes, and what late and defective parts add on top.",
        tags=["Cost per unit", "Cost of poor quality", "Freight"])
if ui.empty_guard(pr):
    st.stop()

k = m.headline_kpis(d)
pe = m.plant_efficiency(pr)
copp = m.cost_of_poor_performance(po, qi)
ui.kpi_row([
    ui.kpi("Total production cost", ui.fmt_money(k["total_prod_cost"]), f"{k['good_units']:,} good units", ui.BLUE),
    ui.kpi("Purchased parts spend", ui.fmt_money(k["spend"]), f"{len(po):,} lots", ui.AQUA),
    ui.kpi("Idle-line cost", ui.fmt_money(k["downtime_cost"]), "all downtime causes", ui.ORANGE),
    ui.kpi("Rework cost", ui.fmt_money(k["rework_cost"]), "defective incoming parts", ui.MAGENTA),
    ui.kpi("Expedited freight", ui.fmt_money(k["expedite_cost"]), "air freight for late lots", ui.VIOLET),
    ui.kpi("Scrap cost", ui.fmt_money(pr.scrap_cost.sum()), "scrapped units", ui.RED),
])

left, right = st.columns([1, 1])
with left:
    cb = m.cost_breakdown(pr)
    fig = go.Figure()
    for ctype, color in zip(["Material", "Labor", "Overhead", "Scrap"], [ui.BLUE, ui.AQUA, ui.YELLOW, ui.RED]):
        g = cb[cb.cost_type == ctype]
        fig.add_trace(go.Bar(x=g.plant_name, y=g.cost / 1e9, name=ctype, marker_color=color,
                             marker_line=dict(color="#fff", width=2),
                             hovertemplate="%{x}<br>" + ctype + ": $%{y:,.2f}B<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="Cost ($ billions)", tickprefix="$", ticksuffix="B")
    ui.show(ui.style(fig, height=380, title="Production cost breakdown by plant"))
with right:
    s = copp.sort_values("total")
    fig = go.Figure()
    for col, color in [("Rework (quality)", ui.MAGENTA), ("Expedited freight (delay)", ui.ORANGE)]:
        fig.add_trace(go.Bar(y=s.supplier_name, x=s[col] / 1e6, orientation="h", name=col, marker_color=color,
                             marker_line=dict(color="#fff", width=2),
                             hovertemplate="%{y}<br>" + col + ": $%{x:,.2f}M<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Cost ($ millions)", tickprefix="$", ticksuffix="M")
    ui.show(ui.style(fig, height=380, title="Cost of poor supplier performance"))

ui.section("Cost per good unit — monthly trend",
           "One small chart per plant because a truck, an SUV and an axle have very different unit costs.")
mp = m.monthly_production(pr)
cols = st.columns(max(1, mp.plant_name.nunique()))
for col, (plant, g) in zip(cols, mp.groupby("plant_name")):
    with col:
        fig = go.Figure(go.Scatter(x=g.month, y=g.cost_per_unit, mode="lines+markers",
                                   line=dict(color=ui.PLANT_COLORS[plant], width=2), marker=dict(size=7),
                                   hovertemplate="%{x|%b %Y}<br>$%{y:,.0f} per unit<extra></extra>"))
        avg = g.total_cost.sum() / g.good.sum()
        fig.add_hline(y=avg, line=dict(color=ui.MUTED, dash="dot", width=1))
        fig.update_yaxes(tickprefix="$", title=None)
        ui.show(ui.style(fig, height=260, title=f"{plant} <sup>· avg ${avg:,.0f} / unit</sup>", legend=False))

left, right = st.columns([1, 1])
with left:
    fm = (po.groupby("transport_mode").agg(freight=("freight_cost", "sum"), value=("po_value", "sum"),
                                           lots=("po_id", "count")).reset_index())
    fm["pct"] = 100 * fm.freight / fm.value
    fm = fm.sort_values("pct")
    mode_colors = {"Road": ui.BLUE, "Rail": ui.AQUA, "Sea": ui.VIOLET, "Air": ui.ORANGE}
    fig = go.Figure(go.Bar(x=fm.transport_mode, y=fm.pct, marker_color=[mode_colors[x] for x in fm.transport_mode],
                           text=[f"{v:.2f}%" for v in fm.pct], textposition="outside", customdata=fm[["lots", "freight"]],
                           hovertemplate="%{x}<br>Freight = %{y:.2f}% of part value<br>%{customdata[0]} lots"
                                         "<br>$%{customdata[1]:,.0f}<extra></extra>"))
    fig.update_yaxes(title="Freight as % of part value", ticksuffix="%")
    ui.show(ui.style(fig, title="Freight cost intensity by transport mode", legend=False))
with right:
    cpu = pe[["plant_name", "good", "total_cost", "cost_per_unit", "downtime_cost"]].copy()
    cpu["downtime_cost_per_unit"] = cpu.downtime_cost / cpu.good
    st.dataframe(cpu, hide_index=True, width="stretch",
                 column_config={
                     "plant_name": "Plant",
                     "good": st.column_config.NumberColumn("Good units", format="%d"),
                     "total_cost": st.column_config.NumberColumn("Total cost ($)", format="%.0f"),
                     "cost_per_unit": st.column_config.NumberColumn("Cost / unit ($)", format="%.0f"),
                     "downtime_cost": st.column_config.NumberColumn("Idle-line cost ($)", format="%.0f"),
                     "downtime_cost_per_unit": st.column_config.NumberColumn("Idle cost / unit ($)", format="%.0f"),
                 })
    st.caption("Air freight is used only to rescue late lots — it costs roughly 5–10× more per dollar of parts "
               "than road, rail or sea, so every late delivery that gets expedited is a direct cost of the delay.")
ui.footer()
