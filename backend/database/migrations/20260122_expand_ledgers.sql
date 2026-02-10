-- Migration to expand ledgers table
-- Run this against k24_shadow.db

ALTER TABLE ledgers ADD COLUMN alias VARCHAR;
ALTER TABLE ledgers ADD COLUMN ledger_type VARCHAR;
ALTER TABLE ledgers ADD COLUMN balance_type VARCHAR;
ALTER TABLE ledgers ADD COLUMN city VARCHAR;
ALTER TABLE ledgers ADD COLUMN state VARCHAR;
ALTER TABLE ledgers ADD COLUMN pincode VARCHAR;
ALTER TABLE ledgers ADD COLUMN country VARCHAR DEFAULT 'India';
ALTER TABLE ledgers ADD COLUMN contact_person VARCHAR;
ALTER TABLE ledgers ADD COLUMN pan VARCHAR;
ALTER TABLE ledgers ADD COLUMN gst_registration_type VARCHAR;
ALTER TABLE ledgers ADD COLUMN is_gst_applicable BOOLEAN DEFAULT 0;
ALTER TABLE ledgers ADD COLUMN credit_limit FLOAT;
ALTER TABLE ledgers ADD COLUMN credit_days INTEGER;
ALTER TABLE ledgers ADD COLUMN tally_guid VARCHAR;
ALTER TABLE ledgers ADD COLUMN created_from VARCHAR DEFAULT 'Manual';

-- Indexes
CREATE INDEX ix_ledgers_ledger_type ON ledgers (ledger_type);
CREATE INDEX ix_ledgers_tally_guid ON ledgers (tally_guid);
CREATE INDEX ix_ledgers_gstin ON ledgers (gstin);
