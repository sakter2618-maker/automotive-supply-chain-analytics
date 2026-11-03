"""
metrics.py
----------
All KPI and analysis logic in plain pandas (no Streamlit code here), so the
same numbers feed the dashboard, the Quality Analytics Report and the Excel
workbook. Each function mirrors a query in sql/03_business_queries.sql.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

OTD_TARGET = 95.0  # contract on-time delivery target (%)


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------
def load_all(data_dir: Path = DATA) -> dict:
    """Read every processed table and attach readable names."""
    d = {name: pd.read_csv(data_dir / f"{name}.csv") for name in
         ["suppliers", "plants", "components", "purchase_orders",
          "quality_inspections", "inventory_daily", "production_daily"]}

    for col in ["order_date", "promised_date", "actual_delivery_date"]:
        d["purchase_orders"][col] = pd.to_datetime(d["purchase_orders"][col])
    d["quality_inspections"]["inspection_date"] = pd.to_datetime(d["quality_inspections"]["inspection_date"])
    d["inventory_daily"]["date"] = pd.to_datetime(d["inventory_daily"]["date"])
    d["production_daily"]["date"] = pd.to_datetime(d["production_daily"]["date"])

    sup = d["suppliers"][["supplier_id", "supplier_name", "region", "tier"]]
    comp = d["components"][["component_id", "component_name", "category", "criticality"]]
    plant = d["plants"][["plant_id", "plant_name"]]
    for t in ["purchase_orders", "quality_inspections"]:
        d[t] = d[t].merge(sup, on="supplier_id").merge(comp, on="component_id").merge(plant, on="plant_id")
    d["inventory_daily"] = (d["inventory_daily"].merge(comp, on="component_id")
                            .merge(d["components"][["component_id", "supplier_id"]], on="component_id")
                            .merge(sup, on="supplier_id").merge(plant, on="plant_id"))
    d["production_daily"] = d["production_daily"].merge(d["plants"], on="plant_id")
    d["production_daily"]["lost_units_shortage"] = (
        d["production_daily"]["planned_units"] * d["production_daily"]["shortage_downtime_hours"]
        / d["production_daily"]["scheduled_hours"])
    return d


def filter_data(d: dict, start, end, plants=None, regions=None) -> dict:
    """Apply the dashboard filters (date range, plant, supplier region)."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    out = dict(d)
    date_col = {"purchase_orders": "promised_date", "quality_inspections": "inspection_date",
                "inventory_daily": "date", "production_daily": "date"}
    for t, col in date_col.items():
        df = d[t]
        m = df[col].between(start, end)
        if plants:
            m &= df["plant_id"].isin(plants)
        if regions and "region" in df.columns:
            m &= df["region"].isin(regions)
        out[t] = df[m]
    return out


# ----------------------------------------------------------------------------
# Headline KPIs
# ----------------------------------------------------------------------------
def headline_kpis(d: dict) -> dict:
    po, qi, inv, pr = d["purchase_orders"], d["quality_inspections"], d["inventory_daily"], d["production_daily"]
    late = po[po.on_time_flag == 0]
    inspected = qi.sample_size.sum()
    return {
        "deliveries": len(po),
        "otd_pct": 100 * po.on_time_flag.mean() if len(po) else np.nan,
        "late_deliveries": len(late),
        "avg_days_late": late.delay_days.mean() if len(late) else 0.0,
        "defect_rate_pct": 100 * qi.defect_qty.sum() / inspected if inspected else np.nan,
        "ppm": 1e6 * qi.defect_qty.sum() / inspected if inspected else np.nan,
        "first_pass_yield_pct": 100 * (qi.inspection_result == "Pass").mean() if len(qi) else np.nan,
        "failed_lots": int((qi.inspection_result == "Fail").sum()),
        "stockout_days": int(inv.stockout_flag.sum()),
        "attainment_pct": 100 * pr.good_units.sum() / pr.planned_units.sum() if len(pr) else np.nan,
        "availability_pct": 100 * (1 - pr.downtime_hours.sum() / pr.scheduled_hours.sum()) if len(pr) else np.nan,
        "units_lost_shortage": pr.lost_units_shortage.sum(),
        "shortage_hours": pr.shortage_downtime_hours.sum(),
        "rework_cost": qi.rework_cost.sum(),
        "expedite_cost": po.loc[po.expedited_flag == 1, "freight_cost"].sum(),
        "spend": po.po_value.sum(),
        "total_prod_cost": pr.total_cost.sum(),
        "good_units": pr.good_units.sum(),
        "downtime_cost": pr.downtime_cost.sum(),
    }


# ----------------------------------------------------------------------------
# Supplier delivery
# ----------------------------------------------------------------------------
def supplier_delivery(po: pd.DataFrame) -> pd.DataFrame:
    g = po.groupby(["supplier_id", "supplier_name", "region"])
    out = g.agg(deliveries=("po_id", "count"), otd_pct=("on_time_flag", "mean"),
                worst_delay=("delay_days", "max"), expedited=("expedited_flag", "sum"),
                fill_rate_pct=("fill_rate_pct", "mean"), spend=("po_value", "sum")).reset_index()
    out["otd_pct"] *= 100
    late = po[po.on_time_flag == 0].groupby("supplier_id").delay_days.mean().rename("avg_days_late")
    out = out.merge(late, on="supplier_id", how="left").fillna({"avg_days_late": 0})
    out["gap_to_target"] = out["otd_pct"] - OTD_TARGET
    return out.sort_values("otd_pct")


def monthly_otd(po: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    keys = [po.promised_date.dt.to_period("M").dt.to_timestamp().rename("month")]
    if by:
        keys.append(po[by])
    out = po.groupby(keys).on_time_flag.mean().mul(100).rename("otd_pct").reset_index()
    return out


def delay_reasons(po: pd.DataFrame) -> pd.DataFrame:
    late = po[po.on_time_flag == 0]
    out = late.groupby("delay_reason").agg(late_deliveries=("po_id", "count"),
                                           avg_days_late=("delay_days", "mean"),
                                           total_days_late=("delay_days", "sum")).reset_index()
    out["share_pct"] = 100 * out.late_deliveries / out.late_deliveries.sum()
    return out.sort_values("late_deliveries", ascending=False)


def delay_buckets(po: pd.DataFrame) -> pd.DataFrame:
    bins = pd.cut(po.delay_days, [-1, 0, 2, 5, 100], labels=["On time", "1-2 days late", "3-5 days late", ">5 days late"])
    out = po.assign(bucket=bins).groupby(["supplier_name", "bucket"], observed=False).po_id.count().rename("lots").reset_index()
    out["share_pct"] = 100 * out.lots / out.groupby("supplier_name").lots.transform("sum")
    return out


# ----------------------------------------------------------------------------
# Quality
# ----------------------------------------------------------------------------
def component_quality(qi: pd.DataFrame) -> pd.DataFrame:
    g = qi.groupby(["component_id", "component_name", "category", "supplier_name"])
    out = g.agg(inspected=("sample_size", "sum"), defects=("defect_qty", "sum"),
                lots=("inspection_id", "count"),
                failed_lots=("inspection_result", lambda s: (s == "Fail").sum()),
                rework_cost=("rework_cost", "sum")).reset_index()
    out["defect_rate_pct"] = 100 * out.defects / out.inspected
    out["ppm"] = 1e6 * out.defects / out.inspected
    return out.sort_values("defect_rate_pct", ascending=False)


def supplier_quality(qi: pd.DataFrame) -> pd.DataFrame:
    g = qi.groupby(["supplier_id", "supplier_name"])
    out = g.agg(inspected=("sample_size", "sum"), defects=("defect_qty", "sum"),
                lots=("inspection_id", "count"),
                passed=("inspection_result", lambda s: (s == "Pass").sum()),
                conditional=("inspection_result", lambda s: (s == "Conditional").sum()),
                failed=("inspection_result", lambda s: (s == "Fail").sum()),
                rework_cost=("rework_cost", "sum")).reset_index()
    out["ppm"] = 1e6 * out.defects / out.inspected
    out["defect_rate_pct"] = out.ppm / 1e4
    out["first_pass_yield_pct"] = 100 * out.passed / out.lots
    return out.sort_values("ppm", ascending=False)


def defect_pareto(qi: pd.DataFrame) -> pd.DataFrame:
    out = (qi[qi.defect_qty > 0].groupby("primary_defect_type").defect_qty.sum()
           .sort_values(ascending=False).rename("defects").reset_index())
    out["share_pct"] = 100 * out.defects / out.defects.sum()
    out["cumulative_pct"] = out.share_pct.cumsum()
    return out


def p_chart(qi: pd.DataFrame, component_id: str) -> pd.DataFrame:
    """Monthly defect proportion with 3-sigma control limits (p-chart)."""
    q = qi[qi.component_id == component_id]
    m = (q.groupby(q.inspection_date.dt.to_period("M").dt.to_timestamp().rename("month"))
         [["defect_qty", "sample_size"]].sum().reset_index())
    p_bar = m.defect_qty.sum() / m.sample_size.sum() if len(m) else 0
    m["defect_rate_pct"] = 100 * m.defect_qty / m.sample_size
    sigma = np.sqrt(p_bar * (1 - p_bar) / m.sample_size)
    m["center_pct"] = 100 * p_bar
    m["ucl_pct"] = 100 * (p_bar + 3 * sigma)
    m["lcl_pct"] = 100 * np.clip(p_bar - 3 * sigma, 0, None)
    m["out_of_control"] = m.defect_rate_pct > m.ucl_pct
    return m


# ----------------------------------------------------------------------------
# Inventory & production
# ----------------------------------------------------------------------------
def stockouts(inv: pd.DataFrame) -> pd.DataFrame:
    g = inv.groupby(["component_name", "supplier_name", "criticality"])
    out = g.agg(stockout_days=("stockout_flag", "sum"), below_safety_days=("below_safety_flag", "sum"),
                units_short=("shortage_qty", "sum"), avg_days_supply=("days_of_supply", "mean")).reset_index()
    return out.sort_values(["stockout_days", "below_safety_days"], ascending=False)


def plant_efficiency(pr: pd.DataFrame) -> pd.DataFrame:
    g = pr.groupby(["plant_id", "plant_name"])
    out = g.agg(planned=("planned_units", "sum"), good=("good_units", "sum"), produced=("produced_units", "sum"),
                scrap=("scrap_units", "sum"), sched=("scheduled_hours", "sum"), down=("downtime_hours", "sum"),
                shortage_hrs=("shortage_downtime_hours", "sum"), lost_units=("lost_units_shortage", "sum"),
                total_cost=("total_cost", "sum"), downtime_cost=("downtime_cost", "sum")).reset_index()
    out["attainment_pct"] = 100 * out.good / out.planned
    out["availability_pct"] = 100 * (1 - out.down / out.sched)
    out["scrap_rate_pct"] = 100 * out.scrap / out.produced
    out["cost_per_unit"] = out.total_cost / out.good
    return out


def downtime_by_cause(pr: pd.DataFrame, by_month: bool = False) -> pd.DataFrame:
    cols = {"shortage_downtime_hours": "Part Shortage", "machine_downtime_hours": "Machine Breakdown",
            "changeover_hours": "Changeover", "quality_hold_hours": "Quality Hold",
            "labor_downtime_hours": "Labor"}
    if by_month:
        g = pr.groupby(pr.date.dt.to_period("M").dt.to_timestamp().rename("month"))[list(cols)].sum()
        return g.rename(columns=cols).reset_index().melt("month", var_name="cause", value_name="hours")
    s = pr[list(cols)].sum().rename(index=cols).sort_values(ascending=False)
    out = s.rename("hours").rename_axis("cause").reset_index()
    out["share_pct"] = 100 * out.hours / out.hours.sum()
    return out


def weekly_delay_impact(po: pd.DataFrame, pr: pd.DataFrame) -> pd.DataFrame:
    """Per plant-week: late critical (A) deliveries vs shortage downtime and lost units."""
    crit = po[po.criticality == "A"].copy()
    crit["week"] = crit.promised_date.dt.to_period("W-SUN").dt.start_time
    late = (crit.groupby(["plant_id", "week"])
            .agg(late_critical=("on_time_flag", lambda s: (s == 0).sum()),
                 days_late_critical=("delay_days", "sum"),
                 max_delay_critical=("delay_days", "max")).reset_index())
    p = pr.copy()
    p["week"] = p.date.dt.to_period("W-SUN").dt.start_time
    prod = (p.groupby(["plant_id", "plant_name", "week"])
            .agg(shortage_hrs=("shortage_downtime_hours", "sum"),
                 lost_units=("lost_units_shortage", "sum"),
                 attainment=("good_units", "sum"), planned=("planned_units", "sum")).reset_index())
    prod["attainment_pct"] = 100 * prod.attainment / prod.planned
    out = prod.merge(late, on=["plant_id", "week"], how="left").fillna(0)
    out["delay_bucket"] = pd.cut(out.max_delay_critical, [-1, 0, 3, 7, 100],
                                 labels=["No late critical parts", "1-3 days late", "4-7 days late", ">7 days late"])
    return out


def delay_impact_summary(weekly: pd.DataFrame) -> pd.DataFrame:
    """Average weekly impact grouped by the worst critical-part delay that week."""
    g = weekly.groupby("delay_bucket", observed=False)
    out = g.agg(plant_weeks=("week", "count"), avg_shortage_hrs=("shortage_hrs", "mean"),
                avg_lost_units=("lost_units", "mean"), attainment_pct=("attainment_pct", "mean")).reset_index()
    return out


def monthly_production(pr: pd.DataFrame) -> pd.DataFrame:
    g = pr.groupby([pr.date.dt.to_period("M").dt.to_timestamp().rename("month"), "plant_name"])
    out = g.agg(planned=("planned_units", "sum"), good=("good_units", "sum"),
                lost=("lost_units_shortage", "sum"), total_cost=("total_cost", "sum"),
                downtime_cost=("downtime_cost", "sum")).reset_index()
    out["attainment_pct"] = 100 * out.good / out.planned
    out["cost_per_unit"] = out.total_cost / out.good
    return out


# ----------------------------------------------------------------------------
# Cost
# ----------------------------------------------------------------------------
def cost_breakdown(pr: pd.DataFrame) -> pd.DataFrame:
    cols = {"material_cost": "Material", "labor_cost": "Labor", "overhead_cost": "Overhead", "scrap_cost": "Scrap"}
    g = pr.groupby("plant_name")[list(cols)].sum().rename(columns=cols)
    return g.reset_index().melt("plant_name", var_name="cost_type", value_name="cost")


def cost_of_poor_performance(po: pd.DataFrame, qi: pd.DataFrame) -> pd.DataFrame:
    rw = qi.groupby("supplier_name").rework_cost.sum().rename("Rework (quality)")
    ex = po[po.expedited_flag == 1].groupby("supplier_name").freight_cost.sum().rename("Expedited freight (delay)")
    out = pd.concat([rw, ex], axis=1).fillna(0)
    out["total"] = out.sum(axis=1)
    return out.sort_values("total", ascending=False).reset_index().rename(columns={"index": "supplier_name"})


# ----------------------------------------------------------------------------
# Supplier scorecard (same formula as SQL Q17)
# ----------------------------------------------------------------------------
def supplier_scorecard(po: pd.DataFrame, qi: pd.DataFrame, suppliers: pd.DataFrame) -> pd.DataFrame:
    dl = supplier_delivery(po)
    ql = supplier_quality(qi)[["supplier_id", "ppm", "first_pass_yield_pct", "rework_cost"]]
    sc = dl.merge(ql, on="supplier_id").merge(
        suppliers[["supplier_id", "tier", "country", "contract_ppm_target"]], on="supplier_id")
    sc["delivery_score"] = sc.otd_pct
    sc["quality_score"] = (100 - sc.ppm / 300).clip(lower=0)
    sc["score"] = 0.45 * sc.delivery_score + 0.40 * sc.quality_score + 0.15 * sc.fill_rate_pct
    sc["rank"] = sc.score.rank(ascending=False, method="min").astype(int)

    def status(r):
        if r.otd_pct >= 92 and r.ppm <= r.contract_ppm_target:
            return "Preferred"
        if r.otd_pct >= 85 and r.ppm <= 2 * r.contract_ppm_target:
            return "Approved - monitor"
        return "Corrective action required"

    sc["status"] = sc.apply(status, axis=1)
    return sc.sort_values("score", ascending=False)
