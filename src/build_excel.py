"""
build_excel.py
--------------
Builds excel/Supplier_Performance_Workbook.xlsx — an Excel version of the
supplier scorecard where every KPI is a live formula (COUNTIFS, SUMIFS,
AVERAGEIFS, INDEX/MATCH) over the raw data sheets.

Run:  python src/build_excel.py
"""

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "excel" / "Supplier_Performance_Workbook.xlsx"
OUT.parent.mkdir(exist_ok=True)

FONT = "Arial"
NAVY, BLUE_FILL, ZEBRA = "0D366B", "DCE9FA", "F6F8FC"
thin = Side(style="thin", color="D9D9D9")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def header(ws, row, headers, widths=None):
    for j, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=j, value=h)
        c.font = Font(name=FONT, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
        if widths:
            ws.column_dimensions[get_column_letter(j)].width = widths[j - 1]
    ws.row_dimensions[row].height = 32


def title(ws, text, sub):
    ws["A1"] = text
    ws["A1"].font = Font(name=FONT, size=16, bold=True, color=NAVY)
    ws["A2"] = sub
    ws["A2"].font = Font(name=FONT, size=10, italic=True, color="52514E")


def body_font(ws, min_row):
    for row in ws.iter_rows(min_row=min_row):
        for c in row:
            if c.font.name != FONT or not c.font.bold:
                c.font = Font(name=FONT, size=10, bold=c.font.bold, color=c.font.color)


def data_sheet(wb, name, df):
    ws = wb.create_sheet(name)
    ws.append(list(df.columns))
    for r in df.itertuples(index=False):
        ws.append(list(r))
    for j, col in enumerate(df.columns, start=1):
        c = ws.cell(row=1, column=j)
        c.font = Font(name=FONT, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        ws.column_dimensions[get_column_letter(j)].width = max(11, min(28, len(col) + 3))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    return ws


sup = pd.read_csv(DATA / "suppliers.csv")
comp = pd.read_csv(DATA / "components.csv")
po = pd.read_csv(DATA / "purchase_orders.csv", parse_dates=["order_date", "promised_date", "actual_delivery_date"])
qi = pd.read_csv(DATA / "quality_inspections.csv", parse_dates=["inspection_date"])
pr = pd.read_csv(DATA / "production_daily.csv", parse_dates=["date"])
plants = pd.read_csv(DATA / "plants.csv")

wb = Workbook()

# ---------------------------------------------------------------- README
ws = wb.active
ws.title = "README"
title(ws, "Automotive Supply Chain & Quality Analytics — Excel Workbook",
      "Portfolio project · Salma Akter · synthetic, reproducible data (src/generate_data.py)")
rows = [
    ("Sheet", "What it shows"),
    ("KPI Summary", "Headline KPIs — all formulas over the data sheets"),
    ("Supplier Scorecard", "OTD %, avg days late, PPM, first-pass yield, fill rate, weighted score, rank, status"),
    ("Component Quality", "Defect rate % and PPM per component (SUMIFS)"),
    ("Monthly OTD", "On-time delivery % by supplier and month (COUNTIFS) with heat-map colors"),
    ("Plant Production", "Attainment, availability, cost per unit by plant"),
    ("Assumptions", "Targets and score weights — change these (blue cells) and every sheet recalculates"),
    ("Data_PO / Data_QI / Data_Production", "Raw data tables (filters on), exported from data/processed/"),
    ("", ""),
    ("Definitions", ""),
    ("OTD %", "On-time deliveries ÷ all deliveries"),
    ("PPM", "Defective parts ÷ inspected parts × 1,000,000"),
    ("First-pass yield", "Lots that passed inspection first time ÷ all lots"),
    ("Score", "Delivery weight × OTD% + Quality weight × MAX(0, 100 − PPM ÷ 300) + Fill weight × Fill rate%"),
    ("Color code", "Blue text = editable input · black = formula"),
]
for i, (a, b) in enumerate(rows, start=4):
    ws.cell(row=i, column=1, value=a).font = Font(name=FONT, bold=True if i in (4, 13) else False, size=10)
    ws.cell(row=i, column=2, value=b).font = Font(name=FONT, size=10)
ws["A4"].font = ws["B4"].font = Font(name=FONT, bold=True, color="FFFFFF")
ws["A4"].fill = ws["B4"].fill = PatternFill("solid", fgColor=NAVY)
ws.column_dimensions["A"].width = 34
ws.column_dimensions["B"].width = 95

# ---------------------------------------------------------------- Assumptions
wa = wb.create_sheet("Assumptions")
title(wa, "Assumptions & targets", "Blue cells are inputs. Source: project design (contract targets used in the analysis).")
inputs = [
    ("OTD target", 0.95, "0.0%", "Contract on-time delivery target"),
    ("PPM target — Tier 1", 5000, "#,##0", "Max defective parts per million, Tier 1"),
    ("PPM target — Tier 2", 8000, "#,##0", "Max defective parts per million, Tier 2"),
    ("Weight — Delivery", 0.45, "0%", "Score weight for OTD %"),
    ("Weight — Quality", 0.40, "0%", "Score weight for quality score"),
    ("Weight — Fill rate", 0.15, "0%", "Score weight for fill rate"),
    ("PPM per quality point", 300, "#,##0", "Quality score = 100 − PPM ÷ this value"),
    ("Preferred: min OTD", 0.92, "0.0%", "Status rule"),
    ("Monitor: min OTD", 0.85, "0.0%", "Status rule"),
]
header(wa, 4, ["Assumption", "Value", "Note"], [30, 14, 55])
for i, (n, v, f, note) in enumerate(inputs, start=5):
    wa.cell(row=i, column=1, value=n)
    c = wa.cell(row=i, column=2, value=v)
    c.number_format = f
    c.font = Font(name=FONT, color="0000FF", size=10)
    c.fill = PatternFill("solid", fgColor="FFF6D5")
    wa.cell(row=i, column=3, value=note)
body_font(wa, 5)
for i in range(5, 5 + len(inputs)):
    wa.cell(row=i, column=2).font = Font(name=FONT, color="0000FF", size=10)
A = {k: f"Assumptions!$B${i}" for i, k in enumerate(
    ["otd", "ppm1", "ppm2", "w_d", "w_q", "w_f", "ppm_pt", "pref", "mon"], start=5)}

# ---------------------------------------------------------------- data sheets (created later in order)
po_x = po.copy()
for c in ["order_date", "promised_date", "actual_delivery_date"]:
    po_x[c] = po_x[c].dt.date
po_x["month"] = po["promised_date"].dt.strftime("%Y-%m")
qi_x = qi.copy()
qi_x["inspection_date"] = qi_x["inspection_date"].dt.date
pr_x = pr.copy()
pr_x["date"] = pr_x["date"].dt.date

N_PO, N_QI, N_PR = len(po_x) + 1, len(qi_x) + 1, len(pr_x) + 1


def col(df, name, sheet, n):
    letter = get_column_letter(list(df.columns).index(name) + 1)
    return f"{sheet}!${letter}$2:${letter}${n}"


P = {c: col(po_x, c, "Data_PO", N_PO) for c in po_x.columns}
Q = {c: col(qi_x, c, "Data_QI", N_QI) for c in qi_x.columns}
R = {c: col(pr_x, c, "Data_Production", N_PR) for c in pr_x.columns}

# ---------------------------------------------------------------- KPI Summary
wk = wb.create_sheet("KPI Summary", 1)
title(wk, "KPI Summary — Jan 2025 to Sep 2026", "Every value below is a live formula over the data sheets.")
header(wk, 4, ["KPI", "Value", "Target", "Status", "Formula logic"], [34, 16, 14, 16, 60])
kpis = [
    ("Deliveries (lots)", f"=COUNTA({P['po_id']})", "#,##0", None, "COUNTA of PO ids"),
    ("On-time delivery %", f"=SUM({P['on_time_flag']})/COUNTA({P['po_id']})", "0.0%", f"={A['otd']}", "on-time ÷ all"),
    ("Avg days late (late lots)", f'=AVERAGEIF({P["on_time_flag"]},0,{P["delay_days"]})', "0.0", None, "AVERAGEIF on late lots"),
    ("Defect rate %", f"=SUM({Q['defect_qty']})/SUM({Q['sample_size']})", "0.00%", None, "defects ÷ inspected"),
    ("Defects per million (PPM)", "=B8*1000000", "#,##0", f"={A['ppm1']}", "defect rate × 1,000,000"),
    ("First-pass yield (lots)", f'=COUNTIF({Q["inspection_result"]},"Pass")/COUNTA({Q["inspection_id"]})', "0.0%", 0.95, "Pass lots ÷ all lots"),
    ("Failed lots", f'=COUNTIF({Q["inspection_result"]},"Fail")', "#,##0", None, "COUNTIF Fail"),
    ("Schedule attainment %", f"=SUM({R['good_units']})/SUM({R['planned_units']})", "0.0%", 0.90, "good ÷ planned units"),
    ("Line availability %", f"=1-SUM({R['downtime_hours']})/SUM({R['scheduled_hours']})", "0.0%", None, "1 − downtime ÷ scheduled"),
    ("Units lost to part shortages", f"=SUMPRODUCT({R['planned_units']},{R['shortage_downtime_hours']})/20", "#,##0", None,
     "planned × shortage hrs ÷ 20 scheduled hrs"),
    ("Rework cost ($)", f"=SUM({Q['rework_cost']})", "$#,##0", None, "SUM rework"),
    ("Expedited freight ($)", f'=SUMIF({P["expedited_flag"]},1,{P["freight_cost"]})', "$#,##0", None, "SUMIF expedited lots"),
    ("Cost of poor supplier performance ($)", "=B15+B16", "$#,##0", None, "rework + expedited freight"),
]
for i, (name, f, fmt, tgt, logic) in enumerate(kpis, start=5):
    wk.cell(row=i, column=1, value=name)
    c = wk.cell(row=i, column=2, value=f)
    c.number_format = fmt
    c.font = Font(name=FONT, bold=True, size=11)
    if tgt is not None:
        t = wk.cell(row=i, column=3, value=tgt)
        t.number_format = fmt
        if not isinstance(tgt, str):
            t.font = Font(name=FONT, color="0000FF", size=10)
        lower_better = "PPM" in name
        cond = f"B{i}<=C{i}" if lower_better else f"B{i}>=C{i}"
        wk.cell(row=i, column=4, value=f'=IF({cond},"✓ On target","✕ Off target")')
    wk.cell(row=i, column=5, value=logic)
    for j in range(1, 6):
        wk.cell(row=i, column=j).border = BORDER
body_font(wk, 5)
for i in range(5, 5 + len(kpis)):
    wk.cell(row=i, column=2).font = Font(name=FONT, bold=True, size=11)
wk.cell(row=18, column=1, value="Targets in blue are inputs (FPY 95%, attainment 90%); OTD and PPM targets link to the Assumptions sheet.").font = Font(name=FONT, italic=True, size=9, color="52514E")

# ---------------------------------------------------------------- Supplier Scorecard
ws = wb.create_sheet("Supplier Scorecard", 2)
title(ws, "Supplier Scorecard", "Score = Delivery 45% + Quality 40% + Fill rate 15% (weights on the Assumptions sheet)")
heads = ["Supplier ID", "Supplier", "Region", "Tier", "Lots", "On-time %", "Avg days late", "Inspected",
         "Defects", "PPM", "PPM target", "First-pass yield", "Fill rate %", "Quality score", "Score", "Rank", "Status"]
header(ws, 4, heads, [11, 28, 12, 9, 8, 11, 11, 11, 9, 10, 10, 11, 10, 10, 9, 7, 26])
n = len(sup)
for i, r in enumerate(sup.itertuples(index=False), start=5):
    ws.cell(row=i, column=1, value=r.supplier_id)
    ws.cell(row=i, column=2, value=r.supplier_name)
    ws.cell(row=i, column=3, value=r.region)
    ws.cell(row=i, column=4, value=r.tier)
    ws.cell(row=i, column=5, value=f"=COUNTIF({P['supplier_id']},A{i})")
    ws.cell(row=i, column=6, value=f"=SUMIF({P['supplier_id']},A{i},{P['on_time_flag']})/E{i}").number_format = "0.0%"
    ws.cell(row=i, column=7, value=f"=IFERROR(AVERAGEIFS({P['delay_days']},{P['supplier_id']},A{i},{P['on_time_flag']},0),0)").number_format = "0.0"
    ws.cell(row=i, column=8, value=f"=SUMIF({Q['supplier_id']},A{i},{Q['sample_size']})").number_format = "#,##0"
    ws.cell(row=i, column=9, value=f"=SUMIF({Q['supplier_id']},A{i},{Q['defect_qty']})").number_format = "#,##0"
    ws.cell(row=i, column=10, value=f"=I{i}/H{i}*1000000").number_format = "#,##0"
    ws.cell(row=i, column=11, value=f'=IF(D{i}="Tier 1",{A["ppm1"]},{A["ppm2"]})').number_format = "#,##0"
    ws.cell(row=i, column=12, value=f'=COUNTIFS({Q["supplier_id"]},A{i},{Q["inspection_result"]},"Pass")/COUNTIF({Q["supplier_id"]},A{i})').number_format = "0.0%"
    ws.cell(row=i, column=13, value=f"=AVERAGEIF({P['supplier_id']},A{i},{P['fill_rate_pct']})").number_format = "0.0"
    ws.cell(row=i, column=14, value=f"=MAX(0,100-J{i}/{A['ppm_pt']})").number_format = "0.0"
    ws.cell(row=i, column=15, value=f"={A['w_d']}*F{i}*100+{A['w_q']}*N{i}+{A['w_f']}*M{i}").number_format = "0.0"
    ws.cell(row=i, column=16, value=f"=RANK(O{i},$O$5:$O${4 + n},0)")
    ws.cell(row=i, column=17, value=(f'=IF(AND(F{i}>={A["pref"]},J{i}<=K{i}),"Preferred",'
                                     f'IF(AND(F{i}>={A["mon"]},J{i}<=2*K{i}),"Approved - monitor","Corrective action required"))'))
    for j in range(1, 18):
        ws.cell(row=i, column=j).border = BORDER
        if i % 2 == 0:
            ws.cell(row=i, column=j).fill = PatternFill("solid", fgColor=ZEBRA)
body_font(ws, 5)
last = 4 + n
ws.conditional_formatting.add(f"F5:F{last}", ColorScaleRule(start_type="min", start_color="F8C9C4",
                                                            mid_type="percentile", mid_value=50, mid_color="FFF6D5",
                                                            end_type="max", end_color="C9E9C9"))
ws.conditional_formatting.add(f"J5:J{last}", ColorScaleRule(start_type="min", start_color="C9E9C9",
                                                            mid_type="percentile", mid_value=50, mid_color="FFF6D5",
                                                            end_type="max", end_color="F8C9C4"))
ws.conditional_formatting.add(f"O5:O{last}", DataBarRule(start_type="num", start_value=0, end_type="num",
                                                         end_value=100, color="2A78D6"))
ws.freeze_panes = "C5"
ws.cell(row=last + 2, column=1, value="Best supplier:").font = Font(name=FONT, bold=True)
ws.cell(row=last + 2, column=2, value=f"=INDEX($B$5:$B${last},MATCH(1,$P$5:$P${last},0))").font = Font(name=FONT, bold=True, color="0CA30C")
ws.cell(row=last + 3, column=1, value="Lowest OTD:").font = Font(name=FONT, bold=True)
ws.cell(row=last + 3, column=2, value=f"=INDEX($B$5:$B${last},MATCH(MIN($F$5:$F${last}),$F$5:$F${last},0))").font = Font(name=FONT, bold=True, color="D03B3B")

# ---------------------------------------------------------------- Component Quality
wq = wb.create_sheet("Component Quality", 3)
title(wq, "Component Quality", "Defect rate and PPM per component — which component has the highest defect rate?")
header(wq, 4, ["Component ID", "Component", "Category", "Supplier ID", "Criticality", "Inspected", "Defects",
               "Defect rate %", "PPM", "Failed lots", "Rework cost ($)", "Rank (worst = 1)"],
       [12, 28, 12, 11, 10, 11, 9, 11, 10, 10, 14, 11])
nc = len(comp)
for i, r in enumerate(comp.itertuples(index=False), start=5):
    wq.cell(row=i, column=1, value=r.component_id)
    wq.cell(row=i, column=2, value=r.component_name)
    wq.cell(row=i, column=3, value=r.category)
    wq.cell(row=i, column=4, value=r.supplier_id)
    wq.cell(row=i, column=5, value=r.criticality)
    wq.cell(row=i, column=6, value=f"=SUMIF({Q['component_id']},A{i},{Q['sample_size']})").number_format = "#,##0"
    wq.cell(row=i, column=7, value=f"=SUMIF({Q['component_id']},A{i},{Q['defect_qty']})").number_format = "#,##0"
    wq.cell(row=i, column=8, value=f"=G{i}/F{i}").number_format = "0.00%"
    wq.cell(row=i, column=9, value=f"=H{i}*1000000").number_format = "#,##0"
    wq.cell(row=i, column=10, value=f'=COUNTIFS({Q["component_id"]},A{i},{Q["inspection_result"]},"Fail")')
    wq.cell(row=i, column=11, value=f"=SUMIF({Q['component_id']},A{i},{Q['rework_cost']})").number_format = "$#,##0"
    wq.cell(row=i, column=12, value=f"=RANK(H{i},$H$5:$H${4 + nc},0)")
    for j in range(1, 13):
        wq.cell(row=i, column=j).border = BORDER
body_font(wq, 5)
wq.conditional_formatting.add(f"H5:H{4 + nc}", DataBarRule(start_type="num", start_value=0, end_type="max", color="E34948"))
wq.freeze_panes = "C5"

# ---------------------------------------------------------------- Monthly OTD
wm = wb.create_sheet("Monthly OTD", 4)
title(wm, "Monthly On-Time Delivery %", "COUNTIFS over Data_PO · red = worse, green = better")
months = sorted(po_x["month"].unique())
header(wm, 4, ["Supplier ID", "Supplier"] + months, [11, 28] + [9] * len(months))
for i, r in enumerate(sup.itertuples(index=False), start=5):
    wm.cell(row=i, column=1, value=r.supplier_id)
    wm.cell(row=i, column=2, value=r.supplier_name)
    for j, mth in enumerate(months, start=3):
        L = get_column_letter(j)
        c = wm.cell(row=i, column=j,
                    value=(f"=IFERROR(COUNTIFS({P['supplier_id']},$A{i},{P['month']},{L}$4,{P['on_time_flag']},1)"
                           f"/COUNTIFS({P['supplier_id']},$A{i},{P['month']},{L}$4),\"\")"))
        c.number_format = "0%"
        c.border = BORDER
body_font(wm, 5)
endc = get_column_letter(2 + len(months))
wm.conditional_formatting.add(f"C5:{endc}{4 + n}", ColorScaleRule(start_type="num", start_value=0.4, start_color="D03B3B",
                                                                  mid_type="num", mid_value=0.85, mid_color="FFF6D5",
                                                                  end_type="num", end_value=1, end_color="0CA30C"))
wm.freeze_panes = "C5"

# ---------------------------------------------------------------- Plant Production
wp = wb.create_sheet("Plant Production", 5)
title(wp, "Plant Production Efficiency & Cost", "SUMIF over Data_Production")
header(wp, 4, ["Plant ID", "Plant", "Planned units", "Good units", "Attainment %", "Downtime hrs",
               "Availability %", "Shortage downtime hrs", "Units lost to shortage", "Total cost ($)",
               "Cost per good unit ($)"], [9, 26, 13, 13, 12, 12, 12, 14, 14, 18, 14])
for i, r in enumerate(plants.itertuples(index=False), start=5):
    wp.cell(row=i, column=1, value=r.plant_id)
    wp.cell(row=i, column=2, value=r.plant_name)
    wp.cell(row=i, column=3, value=f"=SUMIF({R['plant_id']},A{i},{R['planned_units']})").number_format = "#,##0"
    wp.cell(row=i, column=4, value=f"=SUMIF({R['plant_id']},A{i},{R['good_units']})").number_format = "#,##0"
    wp.cell(row=i, column=5, value=f"=D{i}/C{i}").number_format = "0.0%"
    wp.cell(row=i, column=6, value=f"=SUMIF({R['plant_id']},A{i},{R['downtime_hours']})").number_format = "#,##0"
    wp.cell(row=i, column=7, value=f"=1-F{i}/SUMIF({R['plant_id']},A{i},{R['scheduled_hours']})").number_format = "0.0%"
    wp.cell(row=i, column=8, value=f"=SUMIF({R['plant_id']},A{i},{R['shortage_downtime_hours']})").number_format = "#,##0"
    wp.cell(row=i, column=9, value=f"=SUMPRODUCT(({R['plant_id']}=A{i})*{R['planned_units']}*{R['shortage_downtime_hours']})/20").number_format = "#,##0"
    wp.cell(row=i, column=10, value=f"=SUMIF({R['plant_id']},A{i},{R['total_cost']})").number_format = "$#,##0"
    wp.cell(row=i, column=11, value=f"=J{i}/D{i}").number_format = "$#,##0"
    for j in range(1, 12):
        wp.cell(row=i, column=j).border = BORDER
body_font(wp, 5)
wp.cell(row=9, column=1, value="Units lost = planned units × shortage hours ÷ 20 scheduled hours per day (two 10-hour shifts).").font = Font(name=FONT, italic=True, size=9, color="52514E")

# ---------------------------------------------------------------- Data sheets
data_sheet(wb, "Data_PO", po_x)
data_sheet(wb, "Data_QI", qi_x)
data_sheet(wb, "Data_Production", pr_x)

for w in wb.worksheets:
    w.sheet_view.showGridLines = w.title.startswith("Data_")
wb["KPI Summary"].sheet_properties.tabColor = "2A78D6"
wb["Supplier Scorecard"].sheet_properties.tabColor = "1BAF7A"
wb["Component Quality"].sheet_properties.tabColor = "E34948"
wb["Monthly OTD"].sheet_properties.tabColor = "EDA100"
wb["Plant Production"].sheet_properties.tabColor = "6250D6"
wb.save(OUT)
print("saved", OUT)
