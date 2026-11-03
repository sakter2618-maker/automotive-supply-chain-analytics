-- =====================================================================
-- 01_schema.sql  —  Automotive Supply Chain & Quality Analytics
-- Database: PostgreSQL 14+   (tested on PostgreSQL 16)
-- Star-style model: 3 dimension tables + 4 fact tables
-- =====================================================================

DROP TABLE IF EXISTS production_daily, inventory_daily, quality_inspections,
                     purchase_orders, components, suppliers, plants CASCADE;

-- ---------- Dimension tables ----------
CREATE TABLE suppliers (
    supplier_id              VARCHAR(5)  PRIMARY KEY,
    supplier_name            VARCHAR(60) NOT NULL,
    city                     VARCHAR(40),
    country                  VARCHAR(40),
    region                   VARCHAR(20),   -- Domestic / Nearshore / Overseas
    tier                     VARCHAR(10),   -- Tier 1 / Tier 2
    default_mode             VARCHAR(10),   -- Road / Rail / Sea
    contract_otd_target_pct  NUMERIC(5,2),  -- on-time delivery target (%)
    contract_ppm_target      INTEGER        -- max defective parts per million
);

CREATE TABLE plants (
    plant_id           VARCHAR(5) PRIMARY KEY,
    plant_name         VARCHAR(60) NOT NULL,
    daily_plan         INTEGER,         -- planned units per working day
    std_material_cost  NUMERIC(12,2),   -- standard material cost per unit
    labor_per_hr       NUMERIC(12,2)    -- plant labor + burden cost per hour
);

CREATE TABLE components (
    component_id       VARCHAR(5) PRIMARY KEY,
    component_name     VARCHAR(60) NOT NULL,
    category           VARCHAR(20),     -- Body / Powertrain / Chassis / Interior / Electrical
    supplier_id        VARCHAR(5) REFERENCES suppliers(supplier_id),
    unit_cost          NUMERIC(10,2),
    criticality        CHAR(1),         -- A = line stops, B = workaround, C = minor
    units_per_vehicle  INTEGER,
    safety_stock_days  INTEGER
);

-- ---------- Fact tables ----------
CREATE TABLE purchase_orders (
    po_id                 VARCHAR(8) PRIMARY KEY,
    component_id          VARCHAR(5) REFERENCES components(component_id),
    supplier_id           VARCHAR(5) REFERENCES suppliers(supplier_id),
    plant_id              VARCHAR(5) REFERENCES plants(plant_id),
    order_date            DATE,
    promised_date         DATE,
    actual_delivery_date  DATE,
    lead_time_days        INTEGER,
    delay_days            INTEGER,
    on_time_flag          SMALLINT,      -- 1 = on/before promised date
    delay_reason          VARCHAR(30),
    qty_ordered           INTEGER,
    qty_received          INTEGER,
    fill_rate_pct         NUMERIC(6,2),
    transport_mode        VARCHAR(10),
    expedited_flag        SMALLINT,      -- 1 = late lot flown in by air
    unit_cost             NUMERIC(10,2),
    po_value              NUMERIC(14,2),
    freight_cost          NUMERIC(12,2)
);

CREATE TABLE quality_inspections (
    inspection_id        VARCHAR(8) PRIMARY KEY,
    po_id                VARCHAR(8) REFERENCES purchase_orders(po_id),
    component_id         VARCHAR(5) REFERENCES components(component_id),
    supplier_id          VARCHAR(5) REFERENCES suppliers(supplier_id),
    plant_id             VARCHAR(5) REFERENCES plants(plant_id),
    inspection_date      DATE,
    sample_size          INTEGER,
    defect_qty           INTEGER,
    defect_rate_pct      NUMERIC(7,3),
    primary_defect_type  VARCHAR(40),
    inspection_result    VARCHAR(12),   -- Pass / Conditional / Fail
    quarantined_qty      INTEGER,
    rework_cost          NUMERIC(12,2)
);

CREATE TABLE inventory_daily (
    date               DATE,
    plant_id           VARCHAR(5) REFERENCES plants(plant_id),
    component_id       VARCHAR(5) REFERENCES components(component_id),
    received_qty       INTEGER,
    demand_qty         INTEGER,
    shortage_qty       INTEGER,
    closing_stock      INTEGER,
    safety_stock       INTEGER,
    days_of_supply     NUMERIC(8,2),
    stockout_flag      SMALLINT,
    below_safety_flag  SMALLINT,
    PRIMARY KEY (date, plant_id, component_id)
);

CREATE TABLE production_daily (
    date                     DATE,
    plant_id                 VARCHAR(5) REFERENCES plants(plant_id),
    planned_units            INTEGER,
    produced_units           INTEGER,
    good_units               INTEGER,
    scrap_units              INTEGER,
    scheduled_hours          NUMERIC(5,2),
    downtime_hours           NUMERIC(5,2),
    shortage_downtime_hours  NUMERIC(5,2),
    machine_downtime_hours   NUMERIC(5,2),
    changeover_hours         NUMERIC(5,2),
    quality_hold_hours       NUMERIC(5,2),
    labor_downtime_hours     NUMERIC(5,2),
    primary_downtime_cause   VARCHAR(30),
    material_cost            NUMERIC(14,2),
    labor_cost               NUMERIC(14,2),
    overhead_cost            NUMERIC(14,2),
    downtime_cost            NUMERIC(14,2),
    scrap_cost               NUMERIC(14,2),
    total_cost               NUMERIC(14,2),
    cost_per_good_unit       NUMERIC(12,2),
    PRIMARY KEY (date, plant_id)
);

CREATE INDEX idx_po_supplier   ON purchase_orders (supplier_id, promised_date);
CREATE INDEX idx_qi_component  ON quality_inspections (component_id, inspection_date);
CREATE INDEX idx_inv_component ON inventory_daily (component_id, date);
