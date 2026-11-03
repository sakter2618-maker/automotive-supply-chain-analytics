import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

d = ui.data()
po, qi, pr = d["purchase_orders"], d["quality_inspections"], d["production_daily"]

ui.hero("Automotive Supply Chain & Quality Analytics",
        "Supplier delivery, quality, inventory and production performance for 3 Midwest plants and 8 Tier-1/Tier-2 suppliers.",
        tags=["Executive Overview", "Jan 2025 – Sep 2026", "Data Analyst · BI"])

if ui.empty_guard(po) or ui.empty_guard(pr):
    st.stop()

k = m.headline_kpis(d)
ui.kpi_row([
    ui.kpi("On-time delivery", f"{k['otd_pct']:.1f}%", "target 95%", ui.BLUE,
           "good" if k["otd_pct"] >= 95 else ("warn" if k["otd_pct"] >= 90 else "bad")),
    ui.kpi("Avg days late", f"{k['avg_days_late']:.1f} d", f"{k['late_deliveries']:,} late lots", ui.ORANGE),
    ui.kpi("Defect rate", f"{k['defect_rate_pct']:.2f}%", f"{k['ppm']:,.0f} PPM", ui.MAGENTA,
           "good" if k["ppm"] <= 5000 else ("warn" if k["ppm"] <= 8000 else "bad")),
    ui.kpi("First-pass yield", f"{k['first_pass_yield_pct']:.1f}%", f"{k['failed_lots']} failed lots", ui.AQUA),
    ui.kpi("Schedule attainment", f"{k['attainment_pct']:.1f}%", "good units ÷ plan", ui.VIOLET,
           "good" if k["attainment_pct"] >= 90 else ("warn" if k["attainment_pct"] >= 85 else "bad")),
    ui.kpi("Units lost to shortages", f"{k['units_lost_shortage']:,.0f}", f"{k['shortage_hours']:,.0f} line-hours down", ui.RED),
    ui.kpi("Stock-out days", f"{k['stockout_days']}", "component × plant days", ui.YELLOW),
    ui.kpi("Cost of poor supply", ui.fmt_money(k["rework_cost"] + k["expedite_cost"]), "rework + expedited freight", ui.GREEN),
])

# ---------------- Answers to the four business questions ----------------
ui.section("Business questions — answered", "Each answer updates with the sidebar filters.")
dl = m.supplier_delivery(po)
cq = m.component_quality(qi)
sc = m.supplier_scorecard(po, qi, d["suppliers"])
worst, best, bad_comp = dl.iloc[0], sc.iloc[0], cq.iloc[0]
c1, c2, c3, c4 = st.columns(4)
with c1:
    ui.insight("Who is not delivering on time?", worst.supplier_name,
               f"Only {worst.otd_pct:.1f}% on time ({worst.gap_to_target:+.1f} pts vs 95% target); "
               f"late lots arrive {worst.avg_days_late:.1f} days late on average.", ui.RED)
with c2:
    ui.insight("Highest defect rate component?", f"{bad_comp.component_name}",
               f"{bad_comp.defect_rate_pct:.2f}% defective ({bad_comp.ppm:,.0f} PPM) from {bad_comp.supplier_name}; "
               f"{int(bad_comp.failed_lots)} lots failed inspection.", ui.MAGENTA)
with c3:
    share = 100 * k["shortage_hours"] / max(pr.downtime_hours.sum(), 1)
    ui.insight("How much do delays hurt production?", f"{k['units_lost_shortage']:,.0f} units lost",
               f"Part shortages caused {share:.0f}% of all line downtime "
               f"({ui.fmt_money(pr.shortage_downtime_hours.mul(pr.labor_per_hr * 1.6).sum())} idle cost).", ui.ORANGE)
with c4:
    ui.insight("Best performing supplier?", best.supplier_name,
               f"Score {best.score:.1f}/100 — {best.otd_pct:.1f}% on time and {best.ppm:,.0f} PPM.", ui.GREEN)

# ---------------- Trend + scorecard ----------------
left, right = st.columns([3, 2])
with left:
    mo = m.monthly_otd(po)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mo.month, y=mo.otd_pct, mode="lines+markers", name="On-time delivery %",
                             line=dict(color=ui.BLUE, width=2), marker=dict(size=8),
                             hovertemplate="%{x|%b %Y}<br>OTD %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=95, line=dict(color=ui.MUTED, dash="dash", width=1),
                  annotation_text="Target 95%", annotation_position="top left")
    fig.update_yaxes(title="On-time delivery %", ticksuffix="%")
    ui.show(ui.style(fig, title="Monthly on-time delivery — all suppliers", legend=False))
with right:
    s = sc.sort_values("score")
    colors = [ui.STATUS_COLORS[x] for x in s.status]
    fig = go.Figure(go.Bar(x=s.score, y=s.supplier_name, orientation="h", marker_color=colors,
                           text=[f"{v:.0f}" for v in s.score], textposition="outside",
                           customdata=s[["status", "otd_pct", "ppm"]],
                           hovertemplate="<b>%{y}</b><br>Score %{x:.1f}<br>%{customdata[0]}"
                                         "<br>OTD %{customdata[1]:.1f}% · %{customdata[2]:,.0f} PPM<extra></extra>"))
    fig.update_xaxes(range=[0, 110], title="Supplier score (0–100)", tickvals=[0, 25, 50, 75, 100])
    ui.show(ui.style(fig, title="Supplier score (green = preferred, red = action)", legend=False))

left, right = st.columns(2)
with left:
    dt = m.downtime_by_cause(pr)
    fig = go.Figure(go.Bar(x=dt.cause, y=dt.hours, marker_color=[ui.CAUSE_COLORS[c] for c in dt.cause],
                           text=[f"{p:.0f}%" for p in dt.share_pct], textposition="outside",
                           hovertemplate="%{x}<br>%{y:,.0f} hours<extra></extra>"))
    fig.update_yaxes(title="Downtime hours", range=[0, dt.hours.max() * 1.15])
    ui.show(ui.style(fig, title="Line downtime by cause", legend=False))
with right:
    mp = m.monthly_production(pr)
    fig = go.Figure()
    for plant, g in mp.groupby("plant_name"):
        fig.add_trace(go.Scatter(x=g.month, y=g.attainment_pct, mode="lines+markers", name=plant,
                                 line=dict(color=ui.PLANT_COLORS[plant], width=2), marker=dict(size=7),
                                 hovertemplate=plant + "<br>%{x|%b %Y}: %{y:.1f}%<extra></extra>"))
    fig.update_yaxes(title="Schedule attainment %", ticksuffix="%")
    ui.show(ui.style(fig, title="Schedule attainment by plant"))

ui.footer()
