-- Create onboarding_states table
CREATE TABLE IF NOT EXISTS onboarding_states (
    phone VARCHAR(20) PRIMARY KEY,
    current_step VARCHAR(50) NOT NULL DEFAULT 'new',
    temp_data JSONB DEFAULT '{}',
    otp VARCHAR(10),
    otp_expiry TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index on phone is automatic due to PRIMARY KEY
