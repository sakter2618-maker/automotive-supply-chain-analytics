"""
generate_data.py
----------------
Builds the AUTOMOTIVE supply chain dataset used by this project.

Why a generated dataset?
    The public dataset in data/raw/supply_chain_data.csv (100 SKUs, 5 suppliers)
    has no dates, no promised-vs-actual delivery and no production runs, so it
    cannot answer "which supplier delivers late?" or "how much production did
    delays cost?". This script creates a realistic, fully reproducible
    automotive dataset (fixed random seed) and uses the public file's ranges as
    calibration (lead times 1-30 days, defect rates 0-5 %, Pass/Fail inspection,
    Road/Rail/Air/Sea transport).

    All supplier and plant names are FICTIONAL.

Causal chain built into the data (so the analysis has something real to find):
    late delivery  ->  safety stock runs out  ->  part shortage
                   ->  line downtime  ->  lost units  ->  higher cost per unit

Output tables (data/processed/):
    suppliers.csv, components.csv, purchase_orders.csv,
    quality_inspections.csv, inventory_daily.csv, production_daily.csv

Run:  python src/generate_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

START = pd.Timestamp("2025-01-06")  # a Monday
END = pd.Timestamp("2026-09-25")    # a Friday
WORKDAYS = pd.bdate_range(START, END)
WEEKS = pd.date_range(START, END, freq="W-MON")

# --------------------------------------------------------------------------
# 1. Suppliers (fictional)
#    on_time_p      = probability a delivery arrives on/before promised date
#    late_mean      = average days late when a delivery IS late
#    quality_factor = multiplier on component base defect rate
# --------------------------------------------------------------------------
SUPPLIERS = [
    # id, name, city, state/country, region, tier, mode, on_time_p, late_mean, quality_factor, reasons
    ("S01", "Great Lakes Stamping Co.", "Warren", "Michigan, USA", "Domestic", "Tier 1", "Road",
     0.97, 1.5, 0.55, ["Transport Breakdown", "Weather"]),
    ("S02", "Motor City Powertrain Parts", "Livonia", "Michigan, USA", "Domestic", "Tier 1", "Road",
     0.92, 2.0, 0.85, ["Capacity Constraint", "Transport Breakdown", "Weather"]),
    ("S03", "Ohio Valley Castings", "Lima", "Ohio, USA", "Domestic", "Tier 2", "Rail",
     0.86, 3.0, 1.90, ["Quality Rework", "Capacity Constraint", "Raw Material Shortage"]),
    ("S04", "Northshore Seating Systems", "Windsor", "Ontario, Canada", "Nearshore", "Tier 1", "Road",
     0.90, 2.5, 0.80, ["Customs Clearance", "Weather", "Capacity Constraint"]),
    ("S05", "Bajio Wiring Harness", "Queretaro", "Mexico", "Nearshore", "Tier 1", "Rail",
     0.80, 3.5, 1.10, ["Customs Clearance", "Capacity Constraint", "Transport Breakdown"]),
    ("S06", "Pacific Rim Electronics", "Kaohsiung", "Taiwan", "Overseas", "Tier 2", "Sea",
     0.62, 7.0, 1.00, ["Port Congestion", "Raw Material Shortage", "Customs Clearance"]),
    ("S07", "Rhein Precision Bearings", "Schweinfurt", "Germany", "Overseas", "Tier 2", "Sea",
     0.84, 4.0, 0.45, ["Port Congestion", "Customs Clearance"]),
    ("S08", "Hoosier Glass & Trim", "Kokomo", "Indiana, USA", "Domestic", "Tier 1", "Road",
     0.93, 2.0, 0.95, ["Capacity Constraint", "Weather"]),
]
sup = pd.DataFrame(SUPPLIERS, columns=[
    "supplier_id", "supplier_name", "city", "country", "region", "tier", "default_mode",
    "_on_time_p", "_late_mean", "_quality_factor", "_reasons"])
sup["contract_otd_target_pct"] = 95.0
sup["contract_ppm_target"] = np.where(sup["tier"] == "Tier 1", 5000, 8000)

# --------------------------------------------------------------------------
# 2. Components
#    criticality A = line stops without it, B = partial workaround, C = minor
#    base_defect = base defect rate (%) before supplier quality factor
# --------------------------------------------------------------------------
COMPONENTS = [
    # id, name, category, supplier, unit_cost, criticality, base_defect %, units per vehicle, plants
    ("C01", "Door Panel (Outer)", "Body", "S01", 86.0, "A", 0.9, 4, ["DAP", "LAP"]),
    ("C02", "Hood Assembly", "Body", "S01", 142.0, "A", 0.8, 1, ["DAP", "LAP"]),
    ("C03", "Fender Stamping", "Body", "S01", 64.0, "B", 0.7, 2, ["DAP", "LAP"]),
    ("C04", "Crankshaft", "Powertrain", "S02", 310.0, "A", 1.0, 1, ["DAP", "LAP"]),
    ("C05", "Cylinder Head", "Powertrain", "S02", 265.0, "A", 1.3, 1, ["DAP", "LAP"]),
    ("C06", "Transmission Gear Set", "Powertrain", "S02", 420.0, "A", 1.1, 1, ["TDP"]),
    ("C07", "Brake Caliper", "Chassis", "S03", 58.0, "A", 2.0, 4, ["DAP", "LAP"]),
    ("C08", "Steering Knuckle", "Chassis", "S03", 74.0, "A", 1.4, 2, ["DAP", "LAP"]),
    ("C09", "Axle Housing Casting", "Chassis", "S03", 190.0, "A", 1.6, 1, ["TDP"]),
    ("C10", "Front Seat Frame", "Interior", "S04", 135.0, "B", 0.9, 2, ["DAP", "LAP"]),
    ("C11", "Rear Bench Assembly", "Interior", "S04", 160.0, "B", 0.8, 1, ["DAP", "LAP"]),
    ("C12", "Main Wiring Harness", "Electrical", "S05", 225.0, "A", 1.5, 1, ["DAP", "LAP"]),
    ("C13", "Door Wiring Harness", "Electrical", "S05", 38.0, "B", 1.2, 4, ["DAP", "LAP"]),
    ("C14", "Engine Control Unit (ECU)", "Electrical", "S06", 380.0, "A", 1.2, 1, ["DAP", "LAP"]),
    ("C15", "Infotainment Module", "Electrical", "S06", 290.0, "B", 1.8, 1, ["DAP", "LAP"]),
    ("C16", "Sensor Cluster (ADAS)", "Electrical", "S06", 175.0, "A", 1.5, 1, ["DAP", "LAP"]),
    ("C17", "Wheel Bearing", "Powertrain", "S07", 46.0, "A", 0.9, 4, ["DAP", "LAP", "TDP"]),
    ("C18", "Differential Bearing", "Powertrain", "S07", 52.0, "A", 0.8, 2, ["TDP"]),
    ("C19", "Windshield", "Body", "S08", 118.0, "B", 1.3, 1, ["DAP", "LAP"]),
    ("C20", "Interior Trim Kit", "Interior", "S08", 72.0, "C", 1.6, 1, ["DAP", "LAP"]),
]
comp = pd.DataFrame(COMPONENTS, columns=[
    "component_id", "component_name", "category", "supplier_id", "unit_cost",
    "criticality", "_base_defect", "units_per_vehicle", "_plants"])
comp["safety_stock_days"] = np.where(comp["criticality"] == "A", 3, 4)

# --------------------------------------------------------------------------
# 3. Plants (fictional)
# --------------------------------------------------------------------------
PLANTS = {
    "DAP": dict(plant_name="Dearborn Truck Assembly", daily_plan=1150, std_material_cost=21500, labor_per_hr=42000),
    "LAP": dict(plant_name="Lansing SUV Assembly", daily_plan=900, std_material_cost=18800, labor_per_hr=33000),
    "TDP": dict(plant_name="Toledo Drivetrain Plant", daily_plan=1600, std_material_cost=1350, labor_per_hr=21000),
}
SHIFT_HOURS = 20.0  # two 10-hour shifts per working day

# --------------------------------------------------------------------------
# 4-6. Purchase orders, incoming quality inspections and daily inventory
#      Simulated together, week by week, because each weekly order quantity
#      is sized from the stock position (order-up-to policy), and each lot's
#      usable quantity depends on its inspection result.
# --------------------------------------------------------------------------
DEFECT_TYPES = {
    "Body": ["Surface Dent", "Paint/Coating Defect", "Dimensional Out of Tolerance", "Burr / Sharp Edge"],
    "Powertrain": ["Dimensional Out of Tolerance", "Porosity", "Surface Finish", "Hardness Out of Spec"],
    "Chassis": ["Porosity", "Crack", "Dimensional Out of Tolerance", "Machining Defect"],
    "Interior": ["Fabric Defect", "Weld Defect", "Missing Fastener", "Color Mismatch"],
    "Electrical": ["Connector Failure", "Solder Defect", "Software/Flash Error", "Insulation Damage"],
}
DEFECT_SCALE = 0.6           # brings defect rates into the 0.2-4 % band of the source data
FAIL_PCT, COND_PCT = 3.0, 1.5  # inspection decision rules (% defective in sample)


def next_workday(d):
    d = pd.Timestamp(d)
    while d.weekday() >= 5:
        d += pd.Timedelta(days=1)
    return d


sup_idx = sup.set_index("supplier_id")
po_rows, insp_rows, inv_rows = [], [], []
shortage = {}  # (plant, date) -> list of (criticality, shortage_fraction)
po_n = 0

for _, c in comp.iterrows():
    s = sup_idx.loc[c.supplier_id]
    lead_base = {"Road": 7, "Rail": 12, "Sea": 26, "Air": 4}[s.default_mode]
    base_rate = c._base_defect * s._quality_factor * DEFECT_SCALE / 100
    for plant in c._plants:
        need = PLANTS[plant]["daily_plan"] * c.units_per_vehicle
        safety = need * c.safety_stock_days
        on_hand = need * (c.safety_stock_days + 1)
        receipts = {}   # available workday -> usable qty
        open_qty = 0    # ordered but not yet received

        for d in WORKDAYS:
            # ---- every Monday: release the weekly order due this Monday ----
            if d.weekday() == 0:
                wk = d
                po_n += 1
                lead = int(np.clip(rng.normal(lead_base, 2), 1, 30))
                order_date = wk - pd.Timedelta(days=lead)

                # delivery performance
                p_on_time = s._on_time_p
                crunch = c.supplier_id == "S06" and pd.Timestamp("2025-07-01") <= wk <= pd.Timestamp("2025-10-31")
                winter = wk.month in (12, 1, 2) and s.default_mode in ("Road", "Rail")
                if crunch:
                    p_on_time -= 0.25   # semiconductor crunch
                if winter:
                    p_on_time -= 0.06   # winter weather
                if c.supplier_id == "S05" and wk >= pd.Timestamp("2026-01-01"):
                    p_on_time += 0.08   # supplier development program pays off
                if rng.random() < p_on_time:
                    delay = -int(rng.random() < 0.15)
                    reason = "On Time"
                else:
                    delay = int(np.clip(np.ceil(rng.exponential(s._late_mean)), 1, 25))
                    if winter and rng.random() < 0.4:
                        reason = "Weather"
                    elif crunch:
                        reason = "Raw Material Shortage"
                    else:
                        reason = str(rng.choice(s._reasons))
                actual = wk + pd.Timedelta(days=delay)

                # order-up-to: one week of demand + defect allowance + stock correction
                target = safety + need * 5
                position = on_hand + open_qty
                qty_ordered = need * 5 * (1 + base_rate * 1.3) + 0.6 * (target - position)
                qty_ordered = int(max(round(qty_ordered * rng.uniform(0.99, 1.03), -1), need * 2))
                fill = 1.0 if rng.random() < 0.92 else rng.uniform(0.88, 0.99)
                qty_received = int(qty_ordered * fill)

                mode, expedited = s.default_mode, False
                if delay >= 5 and rng.random() < 0.35:
                    mode, expedited = "Air", True
                freight_rate = {"Road": 0.9, "Rail": 0.6, "Sea": 0.45, "Air": 4.8}[mode]
                freight_cost = round(qty_received * c.unit_cost * freight_rate / 100 + rng.uniform(150, 600), 2)

                # incoming inspection (sample)
                rate = base_rate
                if c.component_id == "C07" and pd.Timestamp("2026-03-01") <= wk <= pd.Timestamp("2026-08-31"):
                    rate *= 1.8   # brake caliper porosity (tooling wear)
                if c.component_id == "C15" and wk < pd.Timestamp("2025-12-31"):
                    rate *= 1.4   # infotainment software flashing issue
                rate *= rng.lognormal(0, 0.35)
                sample = int(min(qty_received, rng.choice([200, 315, 500])))
                defects = int(rng.binomial(sample, min(rate, 0.25)))
                d_pct = defects / sample * 100
                result = "Fail" if d_pct > FAIL_PCT else ("Conditional" if d_pct > COND_PCT else "Pass")
                primary = DEFECT_TYPES[c.category][rng.choice(4, p=[0.4, 0.3, 0.2, 0.1])] if defects else "None"
                quarantine = 0.25 if result == "Fail" else 0.0   # part of a failed lot is held for sorting
                usable = int(qty_received * (1 - d_pct / 100) * (1 - quarantine))

                avail = next_workday(actual)
                receipts[avail] = receipts.get(avail, 0) + usable
                open_qty += usable

                po_id = f"PO{po_n:05d}"
                po_rows.append(dict(
                    po_id=po_id, component_id=c.component_id, supplier_id=c.supplier_id,
                    plant_id=plant, order_date=order_date.date(), promised_date=wk.date(),
                    actual_delivery_date=actual.date(), lead_time_days=lead,
                    delay_days=max(delay, 0), on_time_flag=int(delay <= 0), delay_reason=reason,
                    qty_ordered=qty_ordered, qty_received=qty_received,
                    fill_rate_pct=round(qty_received / qty_ordered * 100, 2),
                    transport_mode=mode, expedited_flag=int(expedited),
                    unit_cost=c.unit_cost, po_value=round(qty_received * c.unit_cost, 2),
                    freight_cost=freight_cost))
                insp_rows.append(dict(
                    inspection_id=f"QI{po_n:05d}", po_id=po_id, component_id=c.component_id,
                    supplier_id=c.supplier_id, plant_id=plant,
                    inspection_date=(actual + pd.Timedelta(days=int(rng.integers(0, 2)))).date(),
                    sample_size=sample, defect_qty=defects, defect_rate_pct=round(d_pct, 3),
                    primary_defect_type=primary, inspection_result=result,
                    quarantined_qty=int(qty_received * quarantine),
                    rework_cost=round(defects * c.unit_cost * 0.35 * (qty_received / sample), 2)))

            # ---- daily stock movement ----
            recv = receipts.pop(d, 0)
            on_hand += recv
            open_qty -= recv
            short = max(0, need - on_hand)
            on_hand -= need - short
            if short:
                shortage.setdefault((plant, d), []).append((c.criticality, short / need))
            inv_rows.append(dict(
                date=d.date(), plant_id=plant, component_id=c.component_id,
                received_qty=recv, demand_qty=need, shortage_qty=short,
                closing_stock=on_hand, safety_stock=safety,
                days_of_supply=round(on_hand / need, 2),
                stockout_flag=int(short > 0), below_safety_flag=int(on_hand < safety)))

po = pd.DataFrame(po_rows)
qi = pd.DataFrame(insp_rows)
inv = pd.DataFrame(inv_rows)

# --------------------------------------------------------------------------
# 7. Daily production per plant
# --------------------------------------------------------------------------
STOP_HOURS = {"A": 18.0, "B": 6.0, "C": 1.5}
prod_rows = []
for plant, p in PLANTS.items():
    for d in WORKDAYS:
        s_list = shortage.get((plant, d), [])
        if s_list:
            hrs = sorted((STOP_HOURS[k] * f for k, f in s_list), reverse=True)
            shortage_hrs = min(hrs[0] + 0.3 * sum(hrs[1:]), 18.0)
        else:
            shortage_hrs = 0.0
        machine = rng.exponential(0.8)
        changeover = rng.choice([0, 0, 0, 1.5, 2.0])
        quality_hold = rng.exponential(0.25)
        labor = rng.exponential(0.3) if d.month in (7, 12) else rng.exponential(0.1)
        downtime = min(shortage_hrs + machine + changeover + quality_hold + labor, SHIFT_HOURS)
        causes = {"Part Shortage": shortage_hrs, "Machine Breakdown": machine,
                  "Changeover": changeover, "Quality Hold": quality_hold, "Labor": labor}
        top_cause = max(causes, key=causes.get) if downtime > 0.5 else "None"

        run_hrs = SHIFT_HOURS - downtime
        rate_eff = rng.normal(0.95, 0.025)
        produced = int(p["daily_plan"] * run_hrs / SHIFT_HOURS * rate_eff)
        scrap = int(produced * rng.uniform(0.004, 0.012))
        good = produced - scrap

        material = produced * p["std_material_cost"]
        labor_cost = SHIFT_HOURS * p["labor_per_hr"]          # labor paid even when idle
        overhead = SHIFT_HOURS * p["labor_per_hr"] * 0.6
        downtime_cost = downtime * p["labor_per_hr"] * 1.6      # idle labor + overhead
        scrap_cost = scrap * p["std_material_cost"] * 0.6
        prod_rows.append(dict(
            date=d.date(), plant_id=plant, planned_units=p["daily_plan"],
            produced_units=produced, good_units=good, scrap_units=scrap,
            scheduled_hours=SHIFT_HOURS, downtime_hours=round(downtime, 2),
            shortage_downtime_hours=round(shortage_hrs, 2),
            machine_downtime_hours=round(machine, 2), changeover_hours=round(changeover, 2),
            quality_hold_hours=round(quality_hold, 2), labor_downtime_hours=round(labor, 2),
            primary_downtime_cause=top_cause,
            material_cost=round(material, 2), labor_cost=round(labor_cost, 2),
            overhead_cost=round(overhead, 2), downtime_cost=round(downtime_cost, 2),
            scrap_cost=round(scrap_cost, 2)))
prod = pd.DataFrame(prod_rows)
prod["total_cost"] = prod[["material_cost", "labor_cost", "overhead_cost", "scrap_cost"]].sum(axis=1).round(2)
prod["cost_per_good_unit"] = (prod["total_cost"] / prod["good_units"].clip(lower=1)).round(2)

# --------------------------------------------------------------------------
# 8. Save (drop helper columns that start with "_")
# --------------------------------------------------------------------------
plants = pd.DataFrame([dict(plant_id=k, **v) for k, v in PLANTS.items()])
sup.drop(columns=[c for c in sup.columns if c.startswith("_")]).to_csv(OUT / "suppliers.csv", index=False)
comp.drop(columns=[c for c in comp.columns if c.startswith("_")]).to_csv(OUT / "components.csv", index=False)
plants.to_csv(OUT / "plants.csv", index=False)
po.to_csv(OUT / "purchase_orders.csv", index=False)
qi.to_csv(OUT / "quality_inspections.csv", index=False)
inv.to_csv(OUT / "inventory_daily.csv", index=False)
prod.to_csv(OUT / "production_daily.csv", index=False)

print(f"suppliers {len(sup)} | components {len(comp)} | POs {len(po):,} | inspections {len(qi):,} "
      f"| inventory rows {len(inv):,} | production rows {len(prod):,}")
