-- =====================================================================
-- 02_load_data.sql  —  load the CSV files into PostgreSQL
--
-- Option A (psql command line, run from the project root folder):
--     psql -U postgres -d supply_chain -f sql/01_schema.sql
--     psql -U postgres -d supply_chain -f sql/02_load_data.sql
--
-- Option B (pgAdmin): right-click each table -> Import/Export Data ->
--     choose the CSV in data/processed/, Format = csv, Header = ON.
--     Import in this order: suppliers, plants, components,
--     purchase_orders, quality_inspections, inventory_daily, production_daily
-- =====================================================================

\copy suppliers           FROM 'data/processed/suppliers.csv'           WITH (FORMAT csv, HEADER true);
\copy plants              FROM 'data/processed/plants.csv'              WITH (FORMAT csv, HEADER true);
\copy components          FROM 'data/processed/components.csv'          WITH (FORMAT csv, HEADER true);
\copy purchase_orders     FROM 'data/processed/purchase_orders.csv'     WITH (FORMAT csv, HEADER true);
\copy quality_inspections FROM 'data/processed/quality_inspections.csv' WITH (FORMAT csv, HEADER true);
\copy inventory_daily     FROM 'data/processed/inventory_daily.csv'     WITH (FORMAT csv, HEADER true);
\copy production_daily    FROM 'data/processed/production_daily.csv'    WITH (FORMAT csv, HEADER true);

-- quick row-count check
SELECT 'suppliers' AS table_name, COUNT(*) FROM suppliers
UNION ALL SELECT 'plants', COUNT(*) FROM plants
UNION ALL SELECT 'components', COUNT(*) FROM components
UNION ALL SELECT 'purchase_orders', COUNT(*) FROM purchase_orders
UNION ALL SELECT 'quality_inspections', COUNT(*) FROM quality_inspections
UNION ALL SELECT 'inventory_daily', COUNT(*) FROM inventory_daily
UNION ALL SELECT 'production_daily', COUNT(*) FROM production_daily;
