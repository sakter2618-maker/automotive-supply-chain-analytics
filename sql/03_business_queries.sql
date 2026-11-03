-- =====================================================================
-- 03_business_queries.sql
-- Automotive Supply Chain & Quality Analytics — business questions
-- PostgreSQL 14+ (tested on 16). Run after 01_schema.sql + 02_load_data.sql
--
-- KPI definitions used everywhere in this project
--   OTD %          = on-time deliveries / all deliveries * 100
--   Avg delay      = average days late, counting LATE deliveries only
--   Defect rate %  = defective parts / inspected parts * 100
--   PPM            = defective parts / inspected parts * 1,000,000
--   Schedule attainment % = good units / planned units * 100
--   Availability % = (scheduled hours - downtime hours) / scheduled hours * 100
--   Cost per unit  = total production cost / good units
-- =====================================================================


-- =====================================================================
-- SECTION A. SUPPLIER DELIVERY PERFORMANCE
-- =====================================================================

-- Q1. Business question: Which supplier is NOT delivering on time?
--     On-time delivery %, average delay and gap to the 95 % contract target.
SELECT  s.supplier_id,
        s.supplier_name,
        s.region,
        COUNT(*)                                                    AS deliveries,
        ROUND(100.0 * AVG(po.on_time_flag), 1)                      AS otd_pct,
        ROUND(100.0 * AVG(po.on_time_flag) - s.contract_otd_target_pct, 1) AS gap_to_target_pts,
        ROUND(AVG(po.delay_days) FILTER (WHERE po.on_time_flag = 0), 1)    AS avg_days_late_when_late,
        MAX(po.delay_days)                                          AS worst_delay_days,
        SUM(po.expedited_flag)                                      AS expedited_lots
FROM    purchase_orders po
JOIN    suppliers s USING (supplier_id)
GROUP BY s.supplier_id, s.supplier_name, s.region, s.contract_otd_target_pct
ORDER BY otd_pct ASC;


-- Q2. Monthly OTD trend per supplier (is the problem getting better or worse?)
SELECT  DATE_TRUNC('month', promised_date)::date      AS month,
        supplier_id,
        ROUND(100.0 * AVG(on_time_flag), 1)           AS otd_pct
FROM    purchase_orders
GROUP BY 1, 2
ORDER BY 1, 2;


-- Q3. Supply chain delays — root causes (late deliveries only)
SELECT  delay_reason,
        COUNT(*)                                       AS late_deliveries,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct,
        ROUND(AVG(delay_days), 1)                      AS avg_days_late,
        SUM(delay_days)                                AS total_days_late
FROM    purchase_orders
WHERE   on_time_flag = 0
GROUP BY delay_reason
ORDER BY late_deliveries DESC;


-- Q4. Delay severity buckets per supplier (pivot with FILTER)
SELECT  supplier_id,
        COUNT(*) FILTER (WHERE delay_days = 0)               AS on_time,
        COUNT(*) FILTER (WHERE delay_days BETWEEN 1 AND 2)   AS late_1_2d,
        COUNT(*) FILTER (WHERE delay_days BETWEEN 3 AND 5)   AS late_3_5d,
        COUNT(*) FILTER (WHERE delay_days > 5)               AS late_over_5d
FROM    purchase_orders
GROUP BY supplier_id
ORDER BY late_over_5d DESC;


-- Q5. Lead time & delay by transport mode (and the cost of expediting)
--     Note: 'Air' lots are late lots that were expedited, so their OTD is 0 % by definition.
SELECT  transport_mode,
        COUNT(*)                                AS lots,
        ROUND(AVG(lead_time_days), 1)           AS avg_lead_time_days,
        ROUND(100.0 * AVG(on_time_flag), 1)     AS otd_pct,
        ROUND(SUM(freight_cost) / SUM(po_value) * 100, 2) AS freight_pct_of_value,
        ROUND(SUM(freight_cost))                AS total_freight_cost
FROM    purchase_orders
GROUP BY transport_mode
ORDER BY otd_pct;


-- =====================================================================
-- SECTION B. QUALITY CONTROL & DEFECT RATE
-- =====================================================================

-- Q6. Business question: Which component has the highest defect rate?
SELECT  c.component_id,
        c.component_name,
        c.category,
        s.supplier_name,
        SUM(qi.sample_size)                                         AS inspected,
        SUM(qi.defect_qty)                                          AS defects,
        ROUND(100.0 * SUM(qi.defect_qty) / SUM(qi.sample_size), 2)  AS defect_rate_pct,
        ROUND(1e6 * SUM(qi.defect_qty) / SUM(qi.sample_size))       AS ppm,
        COUNT(*) FILTER (WHERE qi.inspection_result = 'Fail')       AS failed_lots,
        ROUND(SUM(qi.rework_cost))                                  AS rework_cost
FROM    quality_inspections qi
JOIN    components c USING (component_id)
JOIN    suppliers  s ON s.supplier_id = c.supplier_id
GROUP BY c.component_id, c.component_name, c.category, s.supplier_name
ORDER BY defect_rate_pct DESC
LIMIT 10;


-- Q7. Inspection results by supplier (first-pass yield = % lots passed)
SELECT  supplier_id,
        COUNT(*)                                                         AS lots,
        COUNT(*) FILTER (WHERE inspection_result = 'Pass')               AS passed,
        COUNT(*) FILTER (WHERE inspection_result = 'Conditional')        AS conditional,
        COUNT(*) FILTER (WHERE inspection_result = 'Fail')               AS failed,
        ROUND(100.0 * AVG((inspection_result = 'Pass')::int), 1)         AS first_pass_yield_pct
FROM    quality_inspections
GROUP BY supplier_id
ORDER BY first_pass_yield_pct;


-- Q8. Pareto of defect types (which 20 % of causes create 80 % of defects?)
WITH t AS (
    SELECT primary_defect_type, SUM(defect_qty) AS defects
    FROM   quality_inspections
    WHERE  defect_qty > 0
    GROUP BY primary_defect_type
)
SELECT  primary_defect_type,
        defects,
        ROUND(100.0 * defects / SUM(defects) OVER (), 1)                         AS share_pct,
        ROUND(100.0 * SUM(defects) OVER (ORDER BY defects DESC) / SUM(defects) OVER (), 1) AS cumulative_pct
FROM    t
ORDER BY defects DESC;


-- Q9. Monthly defect rate for the worst component (spot the spike)
SELECT  DATE_TRUNC('month', inspection_date)::date               AS month,
        ROUND(100.0 * SUM(defect_qty) / SUM(sample_size), 2)     AS defect_rate_pct,
        COUNT(*) FILTER (WHERE inspection_result = 'Fail')       AS failed_lots
FROM    quality_inspections
WHERE   component_id = 'C07'      -- Brake Caliper
GROUP BY 1
ORDER BY 1;


-- =====================================================================
-- SECTION C. INVENTORY SHORTAGES
-- =====================================================================

-- Q10. Components that ran out of stock (and how often)
SELECT  c.component_name,
        s.supplier_name,
        c.criticality,
        SUM(i.stockout_flag)                        AS stockout_days,
        SUM(i.below_safety_flag)                    AS days_below_safety_stock,
        SUM(i.shortage_qty)                         AS units_short,
        ROUND(AVG(i.days_of_supply), 1)             AS avg_days_of_supply
FROM    inventory_daily i
JOIN    components c USING (component_id)
JOIN    suppliers  s ON s.supplier_id = c.supplier_id
GROUP BY c.component_name, s.supplier_name, c.criticality
HAVING  SUM(i.below_safety_flag) > 0
ORDER BY stockout_days DESC, days_below_safety_stock DESC;


-- =====================================================================
-- SECTION D. PRODUCTION EFFICIENCY & DELAY IMPACT
-- =====================================================================

-- Q11. Production efficiency by plant
SELECT  p.plant_name,
        SUM(pd.planned_units)                                                   AS planned_units,
        SUM(pd.good_units)                                                      AS good_units,
        ROUND(100.0 * SUM(pd.good_units) / SUM(pd.planned_units), 1)            AS schedule_attainment_pct,
        ROUND(100.0 * (SUM(pd.scheduled_hours) - SUM(pd.downtime_hours)) / SUM(pd.scheduled_hours), 1) AS availability_pct,
        ROUND(100.0 * SUM(pd.scrap_units) / SUM(pd.produced_units), 2)          AS scrap_rate_pct
FROM    production_daily pd
JOIN    plants p USING (plant_id)
GROUP BY p.plant_name
ORDER BY schedule_attainment_pct;


-- Q12. Business question: How much is production affected by supply chain delays?
--      Lost units = planned units * (shortage downtime hours / scheduled hours)
SELECT  p.plant_name,
        SUM(pd.shortage_downtime_hours)                                         AS shortage_downtime_hrs,
        ROUND(100.0 * SUM(pd.shortage_downtime_hours) / SUM(pd.downtime_hours), 1) AS share_of_all_downtime_pct,
        COUNT(*) FILTER (WHERE pd.shortage_downtime_hours > 0)                  AS days_hit_by_shortage,
        ROUND(SUM(pd.planned_units * pd.shortage_downtime_hours / pd.scheduled_hours)) AS units_lost_to_shortage,
        ROUND(SUM(pd.shortage_downtime_hours * p.labor_per_hr * 1.6))           AS shortage_downtime_cost
FROM    production_daily pd
JOIN    plants p USING (plant_id)
GROUP BY p.plant_name
ORDER BY units_lost_to_shortage DESC;


-- Q13. Downtime by cause (all plants)
SELECT  cause, ROUND(SUM(hours), 1) AS hours,
        ROUND(100.0 * SUM(hours) / SUM(SUM(hours)) OVER (), 1) AS share_pct
FROM (
    SELECT 'Part Shortage'     AS cause, shortage_downtime_hours AS hours FROM production_daily
    UNION ALL SELECT 'Machine Breakdown', machine_downtime_hours FROM production_daily
    UNION ALL SELECT 'Changeover',        changeover_hours       FROM production_daily
    UNION ALL SELECT 'Quality Hold',      quality_hold_hours     FROM production_daily
    UNION ALL SELECT 'Labor',             labor_downtime_hours   FROM production_daily
) x
GROUP BY cause
ORDER BY hours DESC;


-- Q14. Which supplier's late parts caused the line stoppages?
--      Joins stockout days back to the component's supplier.
SELECT  s.supplier_name,
        COUNT(DISTINCT (i.date, i.plant_id))     AS plant_days_with_stockout,
        SUM(i.shortage_qty)                      AS units_short,
        STRING_AGG(DISTINCT c.component_name, ', ') AS components
FROM    inventory_daily i
JOIN    components c USING (component_id)
JOIN    suppliers  s ON s.supplier_id = c.supplier_id
WHERE   i.stockout_flag = 1
GROUP BY s.supplier_name
ORDER BY plant_days_with_stockout DESC;


-- =====================================================================
-- SECTION E. PRODUCTION COST ANALYSIS
-- =====================================================================

-- Q15. Cost per good unit by plant and quarter
SELECT  p.plant_name,
        TO_CHAR(DATE_TRUNC('quarter', pd.date), 'YYYY-"Q"Q')      AS quarter,
        ROUND(SUM(pd.total_cost) / SUM(pd.good_units), 2)         AS cost_per_good_unit,
        ROUND(SUM(pd.downtime_cost))                              AS downtime_cost,
        ROUND(SUM(pd.scrap_cost))                                 AS scrap_cost
FROM    production_daily pd
JOIN    plants p USING (plant_id)
GROUP BY p.plant_name, DATE_TRUNC('quarter', pd.date)
ORDER BY p.plant_name, quarter;


-- Q16. Cost of poor supplier performance (rework + expedited freight)
SELECT  s.supplier_name,
        ROUND(COALESCE(q.rework_cost, 0))                               AS rework_cost,
        ROUND(COALESCE(f.expedite_freight, 0))                          AS expedited_freight_cost,
        ROUND(COALESCE(q.rework_cost, 0) + COALESCE(f.expedite_freight, 0)) AS cost_of_poor_performance
FROM    suppliers s
LEFT JOIN (SELECT supplier_id, SUM(rework_cost) AS rework_cost
           FROM quality_inspections GROUP BY supplier_id) q USING (supplier_id)
LEFT JOIN (SELECT supplier_id, SUM(freight_cost) AS expedite_freight
           FROM purchase_orders WHERE expedited_flag = 1 GROUP BY supplier_id) f USING (supplier_id)
ORDER BY cost_of_poor_performance DESC;


-- =====================================================================
-- SECTION F. SUPPLIER PERFORMANCE COMPARISON (SCORECARD)
-- =====================================================================

-- Q17. Business question: Which supplier performs best overall?
--      Weighted score (0-100) on absolute scales so it is easy to explain:
--        Delivery score = OTD %                                   weight 45 %
--        Quality score  = 100 - PPM / 300   (0 PPM = 100, 30,000 PPM = 0) weight 40 %
--        Fill score     = average fill rate %                     weight 15 %
WITH d AS (
    SELECT  supplier_id,
            100.0 * AVG(on_time_flag)  AS otd_pct,
            AVG(fill_rate_pct)         AS fill_rate_pct
    FROM    purchase_orders
    GROUP BY supplier_id
), q AS (
    SELECT  supplier_id,
            1e6 * SUM(defect_qty) / SUM(sample_size) AS ppm
    FROM    quality_inspections
    GROUP BY supplier_id
), score AS (
    SELECT  d.supplier_id, d.otd_pct, d.fill_rate_pct, q.ppm,
            0.45 * d.otd_pct
          + 0.40 * GREATEST(0, 100 - q.ppm / 300)
          + 0.15 * d.fill_rate_pct                       AS supplier_score
    FROM d JOIN q USING (supplier_id)
)
SELECT  s.supplier_name,
        ROUND(sc.otd_pct, 1)          AS otd_pct,
        ROUND(sc.ppm)                 AS ppm,
        s.contract_ppm_target         AS ppm_target,
        ROUND(sc.fill_rate_pct, 1)    AS fill_rate_pct,
        ROUND(sc.supplier_score, 1)   AS supplier_score,
        RANK() OVER (ORDER BY sc.supplier_score DESC) AS rank,
        CASE WHEN sc.otd_pct >= 92 AND sc.ppm <= s.contract_ppm_target THEN 'Preferred'
             WHEN sc.otd_pct >= 85 AND sc.ppm <= 2 * s.contract_ppm_target THEN 'Approved - monitor'
             ELSE 'Corrective action required' END       AS status
FROM    score sc
JOIN    suppliers s USING (supplier_id)
ORDER BY supplier_score DESC;


-- Q18. Region comparison: Domestic vs Nearshore vs Overseas
SELECT  s.region,
        ROUND(100.0 * AVG(po.on_time_flag), 1)      AS otd_pct,
        ROUND(AVG(po.lead_time_days), 1)            AS avg_lead_time_days,
        ROUND(SUM(po.po_value) / 1e6, 1)            AS spend_musd
FROM    purchase_orders po
JOIN    suppliers s USING (supplier_id)
GROUP BY s.region
ORDER BY otd_pct DESC;
