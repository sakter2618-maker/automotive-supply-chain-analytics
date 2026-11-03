import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

d = ui.data()
po, qi = d["purchase_orders"], d["quality_inspections"]

ui.hero("Supplier Performance Comparison",
        "One weighted score per supplier: Delivery 45% · Quality 40% · Fill rate 15%.",
        tags=["Scorecard", "Ranking", "Action list"])
if ui.empty_guard(po) or ui.empty_guard(qi):
    st.stop()

sc = m.supplier_scorecard(po, qi, d["suppliers"])
counts = sc.status.value_counts()
best, worst = sc.iloc[0], sc.iloc[-1]
ui.kpi_row([
    ui.kpi("Best supplier", best.supplier_name, f"score {best.score:.1f}", ui.GREEN, "good"),
    ui.kpi("Lowest score", worst.supplier_name, f"score {worst.score:.1f}", ui.RED, "bad"),
    ui.kpi("Preferred", f"{counts.get('Preferred', 0)}", "OTD ≥92% and PPM ≤ target", ui.AQUA),
    ui.kpi("Monitor", f"{counts.get('Approved - monitor', 0)}", "OTD ≥85% and PPM ≤ 2× target", ui.YELLOW),
    ui.kpi("Corrective action", f"{counts.get('Corrective action required', 0)}", "needs a supplier action plan", ui.ORANGE),
])

left, right = st.columns([1, 1])
with left:
    label_set = {sc.iloc[0].supplier_name, sc.iloc[-1].supplier_name, sc.iloc[-2].supplier_name}
    fig = go.Figure()
    for status, color in ui.STATUS_COLORS.items():
        g = sc[sc.status == status]
        if len(g) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=g.otd_pct, y=g.ppm, mode="markers+text", name=status,
            text=[n if n in label_set else "" for n in g.supplier_name], hovertext=g.supplier_name,
            textposition="top center", textfont=dict(size=10, color=ui.INK_2),
            marker=dict(size=g.spend / sc.spend.max() * 40 + 12, color=color, opacity=0.85,
                        line=dict(color="#fff", width=2)),
            customdata=g[["score", "spend"]],
            hovertemplate="<b>%{hovertext}</b><br>OTD %{x:.1f}%<br>%{y:,.0f} PPM<br>Score %{customdata[0]:.1f}"
                          "<br>Spend $%{customdata[1]:,.0f}<extra></extra>"))
    fig.add_vline(x=95, line=dict(color=ui.MUTED, dash="dash", width=1))
    fig.add_hline(y=5000, line=dict(color=ui.MUTED, dash="dash", width=1))
    fig.add_annotation(x=97, y=0, text="Best zone →", showarrow=False, font=dict(color=ui.GOOD, size=11),
                       xanchor="right", yanchor="bottom")
    fig.update_xaxes(title="On-time delivery % (right is better)", ticksuffix="%")
    fig.update_yaxes(title="Defects per million (lower is better)", rangemode="tozero")
    ui.show(ui.style(fig, height=440, title="Delivery vs quality (bubble size = spend)"))
with right:
    s = sc.sort_values("score")
    fig = go.Figure()
    for part, weight, color in [("delivery_score", 0.45, ui.BLUE), ("quality_score", 0.40, ui.MAGENTA),
                                ("fill_rate_pct", 0.15, ui.AQUA)]:
        label = {"delivery_score": "Delivery (45%)", "quality_score": "Quality (40%)", "fill_rate_pct": "Fill rate (15%)"}[part]
        fig.add_trace(go.Bar(y=s.supplier_name, x=s[part] * weight, orientation="h", name=label,
                             marker_color=color, marker_line=dict(color="#fff", width=2),
                             hovertemplate="%{y}<br>" + label + ": %{x:.1f} pts<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(range=[0, 100], title="Score points (max 100)")
    ui.show(ui.style(fig, height=440, title="What makes up each supplier's score"))

ui.section("Supplier scorecard")
tbl = sc[["rank", "supplier_name", "score", "status", "otd_pct", "avg_days_late", "ppm", "contract_ppm_target",
          "first_pass_yield_pct", "fill_rate_pct", "tier", "country"]]
st.dataframe(
    tbl, hide_index=True, width="stretch",
    column_config={
        "rank": "Rank", "supplier_name": "Supplier", "country": "Location", "tier": "Tier",
        "otd_pct": st.column_config.ProgressColumn("On-time %", format="%.1f%%", min_value=0, max_value=100),
        "avg_days_late": st.column_config.NumberColumn("Avg days late", format="%.1f"),
        "ppm": st.column_config.NumberColumn("PPM", format="%.0f"),
        "contract_ppm_target": st.column_config.NumberColumn("PPM target", format="%d"),
        "first_pass_yield_pct": st.column_config.NumberColumn("First-pass yield %", format="%.1f"),
        "fill_rate_pct": st.column_config.NumberColumn("Fill rate %", format="%.1f"),
        "score": st.column_config.ProgressColumn("Score", format="%.1f", min_value=0, max_value=100),
        "status": "Status",
    })

ui.section("Recommended actions")
for _, r in sc[sc.status != "Preferred"].sort_values("score").iterrows():
    issues = []
    if r.otd_pct < 92:
        issues.append(f"on-time delivery {r.otd_pct:.1f}% (target 95%)")
    if r.ppm > r.contract_ppm_target:
        issues.append(f"{r.ppm:,.0f} PPM vs {r.contract_ppm_target:,} target")
    action = ("Open a Supplier Corrective Action Request (SCAR), weekly review, and qualify a second source."
              if r.status == "Corrective action required" else "Monthly performance review and improvement plan.")
    st.markdown(f"**{r.supplier_name}** — {', '.join(issues) if issues else 'borderline metrics'}. {action}")
ui.footer()
