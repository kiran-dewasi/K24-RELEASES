-- Migration to expand items table and create stock_movements
-- Run this against k24_shadow.db

-- 1. Expand items table
ALTER TABLE items ADD COLUMN description VARCHAR;
ALTER TABLE items ADD COLUMN stock_group VARCHAR;
ALTER TABLE items ADD COLUMN stock_category VARCHAR;
ALTER TABLE items ADD COLUMN item_type VARCHAR DEFAULT 'goods';
ALTER TABLE items ADD COLUMN alternate_unit VARCHAR;
ALTER TABLE items ADD COLUMN conversion_factor FLOAT;
ALTER TABLE items ADD COLUMN minimum_stock FLOAT;
ALTER TABLE items ADD COLUMN maximum_stock FLOAT;
ALTER TABLE items ADD COLUMN reorder_quantity FLOAT;
ALTER TABLE items ADD COLUMN mrp FLOAT;
ALTER TABLE items ADD COLUMN valuation_method VARCHAR DEFAULT 'Average';
ALTER TABLE items ADD COLUMN taxability VARCHAR DEFAULT 'Taxable';
ALTER TABLE items ADD COLUMN cess_rate FLOAT DEFAULT 0.0;
ALTER TABLE items ADD COLUMN is_godown_tracking BOOLEAN DEFAULT 0;
ALTER TABLE items ADD COLUMN default_godown VARCHAR;
ALTER TABLE items ADD COLUMN tally_guid VARCHAR;
ALTER TABLE items ADD COLUMN created_from VARCHAR DEFAULT 'Manual';
ALTER TABLE items ADD COLUMN created_at DATETIME;
ALTER TABLE items ADD COLUMN updated_at DATETIME;
ALTER TABLE items ADD COLUMN is_active BOOLEAN DEFAULT 1;

-- Indexes for items
CREATE INDEX ix_items_stock_group ON items (stock_group);
CREATE INDEX ix_items_hsn_code ON items (hsn_code);
CREATE INDEX ix_items_tally_guid ON items (tally_guid);

-- 2. Create stock_movements table
-- Note: SQLite does not support renaming tables easily in all versions if constraints exist.
-- But we can create the new table. 'inventory_entries' was the old name.
-- Strategy: Create stock_movements, and migrate data if any, or just start fresh.
-- Since this is Dev/Shadow DB, we can just create the new table.

CREATE TABLE filtered_stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    voucher_id INTEGER,
    movement_date DATETIME,
    movement_type VARCHAR,
    quantity FLOAT,
    rate FLOAT,
    amount FLOAT,
    godown_name VARCHAR,
    batch_name VARCHAR,
    narration VARCHAR,
    tenant_id VARCHAR NOT NULL DEFAULT 'default',
    FOREIGN KEY(item_id) REFERENCES items(id),
    FOREIGN KEY(voucher_id) REFERENCES vouchers(id)
);

-- Copy data from old inventory_entries if exists (Best Effort)
-- inventory_entries had: id, voucher_id, item_id, actual_qty, billed_qty, rate, amount, is_inward...
-- Map is_inward to movement_type ('IN', 'OUT')

INSERT INTO filtered_stock_movements (id, item_id, voucher_id, quantity, rate, amount, movement_type, godown_name, batch_name, tenant_id)
SELECT id, item_id, voucher_id, billed_qty, rate, amount, CASE WHEN is_inward THEN 'IN' ELSE 'OUT' END, godown_name, batch_name, tenant_id
FROM inventory_entries;

-- Drop old table and rename new one
DROP TABLE inventory_entries;
ALTER TABLE filtered_stock_movements RENAME TO stock_movements;

-- Indexes for stock_movements
CREATE INDEX ix_stock_movements_item_id ON stock_movements (item_id);
CREATE INDEX ix_stock_movements_voucher_id ON stock_movements (voucher_id);
CREATE INDEX ix_stock_movements_movement_date ON stock_movements (movement_date);
