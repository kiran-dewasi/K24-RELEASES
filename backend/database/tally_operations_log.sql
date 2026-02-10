CREATE TABLE tally_operations_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    operation_type VARCHAR(50), -- 'CREATE_LEDGER', 'CREATE_VOUCHER'
    operation_status VARCHAR(20), -- 'PENDING', 'SUCCESS', 'FAILED', 'RETRYING'
    operation_data JSONB, -- original request data
    tally_response JSONB, -- Tally response (success/error)
    error_message TEXT,
    error_decoded JSONB, -- decoded error with solution
    retry_count INT DEFAULT 0,
    retry_at TIMESTAMP,
    created_by_user_id UUID,
    source_pipeline VARCHAR(20) -- 'CHAT' or 'WHATSAPP'
);
