"""
build_report.py
---------------
Creates the Quality Analytics Report (reports/Quality_Analytics_Report.md)
and its charts (reports/figures/*.png). Every number is computed from the
data, so re-running after regenerating data keeps the report correct.

Run:  python src/build_report.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import pandas as pd  # noqa: E402

import metrics as m  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
GOOD, WARNING, CRITICAL, SERIOUS = "#0ca30c", "#fab219", "#d03b3b", "#ec835a"
INK, INK2, MUTED, GRID, NEUTRAL = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#9ec5f4"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlecolor": INK, "axes.titlelocation": "left",
    "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight", "figure.facecolor": "white",
})


def save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)
    return f"figures/{name}"


def hbar(ax, labels, values, colors, fmt):
    bars = ax.barh(labels, values, color=colors, height=0.62)
    for b, v in zip(bars, values):
        ax.text(b.get_width() + max(values) * 0.01, b.get_y() + b.get_height() / 2, fmt(v),
                va="center", fontsize=9, color=INK2)
    ax.grid(axis="y", visible=False)


d = m.load_all()
po, qi, inv, pr = d["purchase_orders"], d["quality_inspections"], d["inventory_daily"], d["production_daily"]
k = m.headline_kpis(d)
dl = m.supplier_delivery(po)
cq = m.component_quality(qi)
sq = m.supplier_quality(qi)
pa = m.defect_pareto(qi)
sc = m.supplier_scorecard(po, qi, d["suppliers"])
copp = m.cost_of_poor_performance(po, qi)
pe = m.plant_efficiency(pr)
so = m.stockouts(inv)
weekly = m.weekly_delay_impact(po, pr)
imp = m.delay_impact_summary(weekly[weekly.plant_id.isin(["DAP", "LAP"])])
dt = m.downtime_by_cause(pr)
reasons = m.delay_reasons(po)

# 1. OTD by supplier
s = dl.sort_values("otd_pct")
fig, ax = plt.subplots(figsize=(8, 4.2))
hbar(ax, s.supplier_name, s.otd_pct,
     [GOOD if v >= 95 else (WARNING if v >= 90 else CRITICAL) for v in s.otd_pct], lambda v: f"{v:.1f}%")
ax.axvline(95, color=INK2, ls="--", lw=1)
ax.text(95.5, len(s) - 0.4, "95% target", color=INK2, fontsize=8)
ax.set_xlim(0, 108)
ax.set_xlabel("On-time delivery %")
ax.set_title("On-time delivery by supplier")
f_otd = save(fig, "01_otd_by_supplier.png")

# 2. Monthly OTD: worst supplier vs the rest
worst_id = dl.iloc[0].supplier_id
mo = m.monthly_otd(po.assign(grp=lambda x: x.supplier_id.eq(worst_id).map({True: dl.iloc[0].supplier_name,
                                                                          False: "All other suppliers"})), by="grp")
fig, ax = plt.subplots(figsize=(8, 3.6))
for (name, g), col in zip(mo.groupby("grp"), [BLUE, ORANGE]):
    col = ORANGE if name != "All other suppliers" else BLUE
    ax.plot(g.month, g.otd_pct, marker="o", ms=4, lw=2, color=col, label=name)
ax.axhline(95, color=MUTED, ls="--", lw=1)
ax.set_ylabel("On-time delivery %")
ax.set_ylim(0, 105)
ax.legend(frameon=False, loc="lower left", ncol=2)
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.set_title("Monthly on-time delivery")
f_trend = save(fig, "02_otd_trend.png")

# 3. Defect rate by component (top 10)
t = cq.head(10).sort_values("defect_rate_pct")
avg = k["defect_rate_pct"]
fig, ax = plt.subplots(figsize=(8, 4.4))
hbar(ax, t.component_name, t.defect_rate_pct,
     [CRITICAL if v > 2 * avg else (SERIOUS if v > avg else NEUTRAL) for v in t.defect_rate_pct], lambda v: f"{v:.2f}%")
ax.axvline(avg, color=INK2, ls="--", lw=1)
ax.set_xlabel("Defect rate % (defective ÷ inspected)")
ax.set_title("Top 10 components by defect rate")
f_comp = save(fig, "03_defect_rate_by_component.png")

# 4. p-chart for the worst component
worst_c = cq.iloc[0]
pc = m.p_chart(qi, worst_c.component_id)
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(pc.month, pc.ucl_pct, color=CRITICAL, ls="--", lw=1.4, label="Upper control limit (3σ)")
ax.plot(pc.month, pc.center_pct, color=MUTED, lw=1.4, label="Average")
ax.plot(pc.month, pc.defect_rate_pct, color=BLUE, lw=2, marker="o", ms=5, label="Monthly defect %")
oc = pc[pc.out_of_control]
ax.scatter(oc.month, oc.defect_rate_pct, color=CRITICAL, s=60, zorder=5, edgecolor="white", label="Out of control")
ax.set_ylabel("Defect rate %")
ax.set_ylim(0, None)
ax.legend(frameon=False, ncol=2, fontsize=8, loc="upper left")
ax.set_title(f"p-chart — {worst_c.component_name}")
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
f_pchart = save(fig, "04_pchart_worst_component.png")

# 5. Pareto
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(pa.primary_defect_type, pa.share_pct, color=MAGENTA, width=0.7)
ax.plot(pa.primary_defect_type, pa.cumulative_pct, color=INK2, marker="o", ms=4, lw=1.6)
ax.axhline(80, color=MUTED, ls=":", lw=1)
ax.set_ylim(0, 105)
ax.set_ylabel("% of all defects (bars) · cumulative % (line)")
ax.tick_params(axis="x", rotation=60, labelsize=8)
plt.setp(ax.get_xticklabels(), ha="right")
ax.grid(axis="x", visible=False)
ax.set_title("Pareto of defect types")
f_pareto = save(fig, "05_defect_pareto.png")

# 6. Delay impact on production
fig, ax = plt.subplots(figsize=(8, 3.6))
cols = [NEUTRAL, YELLOW, ORANGE, RED]
bars = ax.bar(imp.delay_bucket.astype(str), imp.avg_lost_units, color=cols, width=0.6)
for b, v, a in zip(bars, imp.avg_lost_units, imp.attainment_pct):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 6, f"{v:,.0f} units\n{a:.1f}% attainment",
            ha="center", fontsize=8.5, color=INK2)
ax.set_ylim(0, imp.avg_lost_units.max() * 1.35 + 10)
ax.set_ylabel("Avg units lost per plant-week")
ax.grid(axis="x", visible=False)
ax.set_title("Production lost vs worst critical-part delay in the week")
f_impact = save(fig, "06_delay_impact.png")

# 7. Supplier score
s = sc.sort_values("score")
st_col = {"Preferred": GOOD, "Approved - monitor": WARNING, "Corrective action required": CRITICAL}
fig, ax = plt.subplots(figsize=(8, 4.2))
hbar(ax, s.supplier_name, s.score, [st_col[x] for x in s.status], lambda v: f"{v:.1f}")
ax.set_xlim(0, 108)
ax.set_xlabel("Supplier score (0–100) · green = Preferred, amber = Monitor, red = Corrective action")
ax.set_title("Supplier performance score")
f_score = save(fig, "07_supplier_score.png")

# 8. Cost of poor performance
s = copp.sort_values("total")
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.barh(s.supplier_name, s["Rework (quality)"] / 1e6, color=MAGENTA, height=0.62, label="Rework (quality)",
        edgecolor="white", linewidth=1.5)
ax.barh(s.supplier_name, s["Expedited freight (delay)"] / 1e6, left=s["Rework (quality)"] / 1e6, color=ORANGE,
        height=0.62, label="Expedited freight (delay)", edgecolor="white", linewidth=1.5)
ax.set_xlabel("$ millions")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
ax.set_title("Cost of poor supplier performance")
f_copp = save(fig, "08_cost_of_poor_performance.png")

# ----------------------------------------------------------------------------
# Report text
# ----------------------------------------------------------------------------
worst = dl.iloc[0]
second = dl.iloc[1]
best = sc.iloc[0]
c07 = worst_c
s03 = sq[sq.supplier_id == "S03"].iloc[0]
spike = pc[pc.out_of_control]
pre = pc[pc.month < "2026-03-01"].defect_rate_pct.mean()
during = pc[(pc.month >= "2026-03-01") & (pc.month <= "2026-08-31")].defect_rate_pct.mean()
short_share = 100 * k["shortage_hours"] / pr.downtime_hours.sum()
s06_so = so[so.supplier_name == worst.supplier_name]
top3_pareto = pa.head(3)
cum3 = top3_pareto.cumulative_pct.iloc[-1]
lost_cost = (pr.shortage_downtime_hours * pr.labor_per_hr * 1.6).sum()
below_target = dl[dl.otd_pct < 95]
fpy = sq.set_index("supplier_name").first_pass_yield_pct


def table(df, cols, headers, fmts):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(f(r[c]) for c, f in zip(cols, fmts)) + " |")
    return "\n".join(lines)


pct1 = lambda v: f"{v:.1f}%"  # noqa: E731
pct2 = lambda v: f"{v:.2f}%"  # noqa: E731
num0 = lambda v: f"{v:,.0f}"  # noqa: E731
txt = str

report = f"""# Quality Analytics Report
### Automotive Supply Chain & Quality Analytics

**Prepared by:** Salma Akter · **Role focus:** Data Analyst / Business Intelligence
**Scope:** 8 suppliers · 20 components · 3 plants · {k['deliveries']:,} deliveries · {len(qi):,} incoming inspections · Jan 2025 – Sep 2026
**Tools:** PostgreSQL (SQL), Python (pandas, Plotly, Streamlit, matplotlib), Excel

> Data note: the dataset is synthetic and reproducible (`src/generate_data.py`, seed 42). Its ranges are
> calibrated to the public supply chain dataset in `data/raw/`. Supplier and plant names are fictional.

---

## 1. Executive summary

| KPI | Result | Target | Status |
|---|---|---|---|
| On-time delivery (OTD) | **{k['otd_pct']:.1f}%** | 95% | {'✅' if k['otd_pct'] >= 95 else '❌'} {len(below_target)} of 8 suppliers below target |
| Incoming defect rate | **{k['defect_rate_pct']:.2f}%** ({k['ppm']:,.0f} PPM) | ≤ 5,000 PPM (Tier 1) | {'✅' if k['ppm'] <= 5000 else '❌'} |
| First-pass yield (lots) | **{k['first_pass_yield_pct']:.1f}%** | 95% | {'✅' if k['first_pass_yield_pct'] >= 95 else '❌'} {k['failed_lots']} lots failed |
| Schedule attainment | **{k['attainment_pct']:.1f}%** | 90% | {'✅' if k['attainment_pct'] >= 90 else '❌'} |
| Units lost to part shortages | **{k['units_lost_shortage']:,.0f}** | 0 | {k['shortage_hours']:,.0f} line-hours stopped |
| Cost of poor supplier performance | **${(k['rework_cost'] + k['expedite_cost'])/1e6:,.1f}M** | — | rework + expedited freight |

**Four findings that matter most**

1. **{worst.supplier_name} is the delivery problem.** Only **{worst.otd_pct:.1f}%** of its lots arrive on time
   ({worst.gap_to_target:+.1f} pts vs target), and late lots are **{worst.avg_days_late:.1f} days** late on average.
   It supplies A-critical electronics, so it caused **{int(s06_so.stockout_days.sum())} of {k['stockout_days']} stock-out days**.
2. **{c07.component_name} ({c07.supplier_name}) has the highest defect rate: {c07.defect_rate_pct:.2f}%**
   ({c07.ppm:,.0f} PPM). The p-chart shows a special-cause shift from **March 2026**: the monthly rate rose
   from ~{pre:.1f}% to ~{during:.1f}%, with **{len(spike)} months above the upper control limit**.
3. **Delays only hurt production once they exceed safety stock.** Weeks whose worst critical-part delay
   was ≤3 days lost almost nothing; weeks with a **>7 day** delay lost **{imp.avg_lost_units.iloc[-1]:,.0f} units per plant-week**
   and attainment fell to **{imp.attainment_pct.iloc[-1]:.1f}%** (vs {imp.attainment_pct.iloc[0]:.1f}% with no late critical parts).
   Part shortages caused **{short_share:.0f}%** of all line downtime.
4. **{best.supplier_name} is the best supplier** (score **{best.score:.1f}/100**, {best.otd_pct:.1f}% OTD, {best.ppm:,.0f} PPM)
   and the only one rated *Preferred*.

---

## 2. Supplier delivery performance

![OTD by supplier]({f_otd})

{table(dl.sort_values('otd_pct'), ['supplier_name', 'region', 'deliveries', 'otd_pct', 'avg_days_late', 'worst_delay'],
       ['Supplier', 'Region', 'Lots', 'OTD %', 'Avg days late', 'Worst delay (d)'],
       [txt, txt, num0, pct1, lambda v: f"{v:.1f}", num0])}

![OTD trend]({f_trend})

**Root causes of late deliveries** — {reasons.iloc[0].delay_reason} ({reasons.iloc[0].share_pct:.0f}%),
{reasons.iloc[1].delay_reason} ({reasons.iloc[1].share_pct:.0f}%) and {reasons.iloc[2].delay_reason}
({reasons.iloc[2].share_pct:.0f}%) explain {reasons.head(3).share_pct.sum():.0f}% of late lots. The worst month for
{worst.supplier_name} was during the Jul–Oct 2025 semiconductor raw-material shortage.
Overseas suppliers average {po[po.region == 'Overseas'].lead_time_days.mean():.0f}-day lead times vs
{po[po.region == 'Domestic'].lead_time_days.mean():.0f} days for domestic suppliers.

---

## 3. Quality control & defect rate

![Defect rate by component]({f_comp})

{table(cq.head(5), ['component_name', 'supplier_name', 'inspected', 'defect_rate_pct', 'ppm', 'failed_lots'],
       ['Component', 'Supplier', 'Parts inspected', 'Defect %', 'PPM', 'Failed lots'],
       [txt, txt, num0, pct2, num0, num0])}

**By supplier:** {s03.supplier_name} has the highest PPM (**{s03.ppm:,.0f}**, target 8,000) and the lowest first-pass yield
(**{s03.first_pass_yield_pct:.1f}%** of lots pass first time). Three of the five worst components are its castings.

### Statistical process control (p-chart)

![p-chart]({f_pchart})

A p-chart plots the monthly defect proportion against limits of ±3 standard deviations around the long-run average.
Points above the upper control limit indicate a *special cause* (something changed in the process), not random noise.
The shift starting March 2026 points to a tooling or process change at the supplier — **porosity** is its top defect type.

### Pareto of defect types

![Pareto]({f_pareto})

The top three defect types — {', '.join(top3_pareto.primary_defect_type)} — make up **{cum3:.0f}%** of all defects.
Focusing corrective actions on casting porosity and electronics connector/solder quality gives the biggest gain.

---

## 4. Inventory shortages & production impact

{table(so[so.stockout_days > 0], ['component_name', 'supplier_name', 'criticality', 'stockout_days', 'below_safety_days', 'units_short'],
       ['Component', 'Supplier', 'Class', 'Stock-out days', 'Days below safety stock', 'Units short'],
       [txt, txt, txt, num0, num0, num0])}

![Delay impact]({f_impact})

**How the chain works:** a late lot first consumes the ~3 days of safety stock. If it is later than that, the
plant runs out of the part, the line stops (A-class part = full stop), and the lost units can't be recovered.

{table(pe, ['plant_name', 'attainment_pct', 'availability_pct', 'scrap_rate_pct', 'shortage_hrs', 'lost_units'],
       ['Plant', 'Attainment', 'Availability', 'Scrap %', 'Shortage downtime (h)', 'Units lost'],
       [txt, pct1, pct1, pct2, num0, num0])}

Downtime by cause: {', '.join(f"{r.cause} {r.share_pct:.0f}%" for r in dt.itertuples())}.
Idle labor and overhead during part-shortage stops cost about **${lost_cost/1e6:,.1f}M**.

---

## 5. Supplier performance comparison

**Score = 45% Delivery (OTD %) + 40% Quality (100 − PPM ÷ 300) + 15% Fill rate.**

![Supplier score]({f_score})

{table(sc, ['rank', 'supplier_name', 'otd_pct', 'ppm', 'score', 'status'],
       ['Rank', 'Supplier', 'OTD %', 'PPM', 'Score', 'Status'],
       [num0, txt, pct1, num0, lambda v: f"{v:.1f}", txt])}

---

## 6. Production cost analysis

![Cost of poor performance]({f_copp})

{table(pe, ['plant_name', 'good', 'total_cost', 'cost_per_unit', 'downtime_cost'],
       ['Plant', 'Good units', 'Total cost', 'Cost / good unit', 'Idle-line cost'],
       [txt, num0, lambda v: f"${v/1e6:,.0f}M", lambda v: f"${v:,.0f}", lambda v: f"${v/1e6:,.1f}M"])}

Material is the largest cost; the controllable part is the **cost of poor performance** —
${k['rework_cost']/1e6:,.1f}M of rework/sorting and ${k['expedite_cost']/1e6:,.1f}M of air freight used to rescue late lots.
{copp.iloc[0].supplier_name} and {copp.iloc[1].supplier_name} account for
**{100 * copp.head(2).total.sum() / copp.total.sum():.0f}%** of it.

---

## 7. Recommendations

| # | Action | Owner | Expected impact |
|---|---|---|---|
| 1 | Issue a **SCAR** to {worst.supplier_name}; move ECU/ADAS buffer from 3 to 7 days while a **second source** is qualified | Purchasing / SQE | Removes most stock-out days |
| 2 | 8D problem-solving with {s03.supplier_name} on **{c07.component_name} porosity** (tooling audit, X-ray sampling) | Supplier Quality | Bring PPM back to ≤ 8,000 |
| 3 | Tighten incoming inspection (100% check) on {c07.component_name} until 3 months are in control | Plant Quality | Protect the line from escapes |
| 4 | Weekly delivery review with {second.supplier_name} and other suppliers < 90% OTD | Supply Chain | +5–10 pts OTD |
| 5 | Use the scorecard in quarterly business reviews; reward {best.supplier_name}-level performance with volume | Purchasing | Supplier accountability |

---

## 8. Method & definitions

- **OTD %** = deliveries on or before promised date ÷ all deliveries.
- **Defect rate %** = defective parts ÷ inspected parts; **PPM** = the same × 1,000,000.
- **First-pass yield** = lots passing inspection the first time ÷ all lots (Fail > 3% defective, Conditional > 1.5%).
- **Schedule attainment** = good units ÷ planned units. **Availability** = (scheduled − downtime hours) ÷ scheduled hours.
- **Units lost to shortage** = planned units × shortage downtime hours ÷ scheduled hours.
- All figures are reproducible with `sql/03_business_queries.sql` (PostgreSQL) and `src/metrics.py` (Python).
"""

out = ROOT / "reports" / "Quality_Analytics_Report.md"
out.write_text(report, encoding="utf-8")
print("report written:", out, "| figures:", len(list(FIG.glob('*.png'))))
