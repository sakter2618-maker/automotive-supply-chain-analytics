import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

d = ui.data()
po, inv, pr = d["purchase_orders"], d["inventory_daily"], d["production_daily"]

ui.hero("Inventory Shortages & Production Efficiency",
        "How late parts drain safety stock, stop the line and cost finished units.",
        tags=["Inventory", "Downtime", "Delay → production impact"])
if ui.empty_guard(inv) or ui.empty_guard(pr):
    st.stop()

k = m.headline_kpis(d)
pe = m.plant_efficiency(pr)
ui.kpi_row([
    ui.kpi("Schedule attainment", f"{k['attainment_pct']:.1f}%", "good units ÷ plan", ui.BLUE,
           "good" if k["attainment_pct"] >= 90 else ("warn" if k["attainment_pct"] >= 85 else "bad")),
    ui.kpi("Line availability", f"{k['availability_pct']:.1f}%", "scheduled hrs not down", ui.AQUA),
    ui.kpi("Scrap rate", f"{100 * pr.scrap_units.sum() / pr.produced_units.sum():.2f}%", "of produced units", ui.MAGENTA),
    ui.kpi("Stock-out days", f"{k['stockout_days']}", f"{int(inv.below_safety_flag.sum()):,} days below safety stock", ui.YELLOW),
    ui.kpi("Shortage downtime", f"{k['shortage_hours']:,.0f} h", "line stopped for parts", ui.ORANGE),
    ui.kpi("Units lost to shortages", f"{k['units_lost_shortage']:,.0f}", "vehicles / axles not built", ui.RED),
])

# ---------------- Delay → production impact ----------------
ui.section("How much do supply chain delays affect production?",
           "Each plant-week is grouped by its worst late critical (A-class) part. Safety stock covers ~3 days — "
           "beyond that, the line stops.")
w = m.weekly_delay_impact(po, pr)
w = w[w.plant_id.isin(["DAP", "LAP"])] if w.plant_id.isin(["DAP", "LAP"]).any() else w
imp = m.delay_impact_summary(w)
c1, c2 = st.columns(2)
bucket_colors = [ui.NEUTRAL_BAR, ui.YELLOW, ui.ORANGE, ui.RED]
with c1:
    fig = go.Figure(go.Bar(x=imp.delay_bucket.astype(str), y=imp.avg_lost_units, marker_color=bucket_colors,
                           text=[f"{v:,.0f}" for v in imp.avg_lost_units], textposition="outside",
                           customdata=imp.plant_weeks,
                           hovertemplate="%{x}<br>%{y:,.0f} units lost per week<br>%{customdata} plant-weeks<extra></extra>"))
    fig.update_yaxes(title="Avg units lost per plant-week")
    ui.show(ui.style(fig, title="Units lost per week vs worst critical-part delay", legend=False))
with c2:
    fig = go.Figure(go.Bar(x=imp.delay_bucket.astype(str), y=imp.attainment_pct, marker_color=bucket_colors,
                           text=[f"{v:.1f}%" for v in imp.attainment_pct], textposition="outside",
                           hovertemplate="%{x}<br>Attainment %{y:.1f}%<extra></extra>"))
    lo = max(0, imp.attainment_pct.min() - 10) if imp.attainment_pct.notna().any() else 0
    fig.update_yaxes(title="Avg schedule attainment %", ticksuffix="%", range=[lo, 100])
    ui.show(ui.style(fig, title="Schedule attainment vs worst critical-part delay (assembly plants)", legend=False))

# ---------------- Stock-outs ----------------
left, right = st.columns([1, 1])
so = m.stockouts(inv)
with left:
    top = so[so.below_safety_days > 0].head(10).sort_values("below_safety_days")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=top.component_name, x=top.below_safety_days, orientation="h", name="Days below safety stock",
                         marker_color=ui.YELLOW, hovertemplate="%{y}<br>%{x} days below safety stock<extra></extra>"))
    fig.add_trace(go.Bar(y=top.component_name, x=top.stockout_days, orientation="h", name="Stock-out days",
                         marker_color=ui.RED, hovertemplate="%{y}<br>%{x} stock-out days<extra></extra>"))
    fig.update_layout(barmode="group", bargroupgap=0.1)
    fig.update_xaxes(title="Days (component × plant)")
    ui.show(ui.style(fig, height=420, title="Inventory shortage risk by component"))
with right:
    comps = so.component_name.tolist()
    choice = st.selectbox("Component stock level", comps, index=0)
    plants_avail = sorted(inv[inv.component_name == choice].plant_name.unique())
    plant = st.radio("Plant", plants_avail, horizontal=True, label_visibility="collapsed")
    s = inv[(inv.component_name == choice) & (inv.plant_name == plant)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.date, y=s.days_of_supply, mode="lines", name="Days of supply",
                             line=dict(color=ui.BLUE, width=1.6),
                             hovertemplate="%{x|%d %b %Y}<br>%{y:.1f} days of supply<extra></extra>"))
    ss = s.safety_stock.iloc[0] / s.demand_qty.iloc[0] if len(s) else 3
    fig.add_hline(y=ss, line=dict(color=ui.SERIOUS, dash="dash", width=1.2),
                  annotation_text=f"Safety stock ({ss:.0f} days)", annotation_position="top left")
    out = s[s.stockout_flag == 1]
    fig.add_trace(go.Scatter(x=out.date, y=out.days_of_supply, mode="markers", name="Stock-out day",
                             marker=dict(color=ui.CRITICAL, size=9, symbol="x"),
                             hovertemplate="%{x|%d %b %Y}<br>STOCK-OUT<extra></extra>"))
    fig.update_yaxes(title="Days of supply on hand", rangemode="tozero")
    ui.show(ui.style(fig, height=350, title=f"{choice} — {plant}"))

# ---------------- Production efficiency ----------------
ui.section("Production efficiency by plant")
left, right = st.columns([1, 1])
with left:
    dm = m.downtime_by_cause(pr, by_month=True)
    fig = go.Figure()
    for cause, color in ui.CAUSE_COLORS.items():
        g = dm[dm.cause == cause]
        fig.add_trace(go.Bar(x=g.month, y=g.hours, name=cause, marker_color=color,
                             marker_line=dict(color="#fff", width=1),
                             hovertemplate="%{x|%b %Y}<br>" + cause + ": %{y:,.0f} h<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="Downtime hours")
    ui.show(ui.style(fig, height=380, title="Monthly downtime by cause (red = part shortage)"))
with right:
    st.dataframe(
        pe[["plant_name", "planned", "good", "attainment_pct", "availability_pct", "scrap_rate_pct",
            "shortage_hrs", "lost_units"]],
        hide_index=True, width="stretch",
        column_config={
            "plant_name": "Plant",
            "planned": st.column_config.NumberColumn("Planned units", format="%d"),
            "good": st.column_config.NumberColumn("Good units", format="%d"),
            "attainment_pct": st.column_config.ProgressColumn("Attainment", format="%.1f%%", min_value=0, max_value=100),
            "availability_pct": st.column_config.ProgressColumn("Availability", format="%.1f%%", min_value=0, max_value=100),
            "scrap_rate_pct": st.column_config.NumberColumn("Scrap %", format="%.2f"),
            "shortage_hrs": st.column_config.NumberColumn("Shortage hrs", format="%.0f"),
            "lost_units": st.column_config.NumberColumn("Units lost", format="%.0f"),
        })
    st.caption("Attainment = good units ÷ planned units. Availability = (scheduled − downtime) ÷ scheduled hours.")
ui.footer()
