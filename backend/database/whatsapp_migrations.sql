-- Create user_whatsapp_mapping table
CREATE TABLE IF NOT EXISTS user_whatsapp_mapping (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    whatsapp_phone VARCHAR(20) UNIQUE,
    user_id UUID, -- Can be linked to auth.users later, currently storing generated string/UUID
    verified BOOLEAN DEFAULT FALSE
);

-- Create whatsapp_raw_messages table
CREATE TABLE IF NOT EXISTS whatsapp_raw_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT NOW(),
    from_phone VARCHAR(20) NOT NULL,
    message_text TEXT NOT NULL,
    message_id VARCHAR(100) UNIQUE NOT NULL,
    webhook_timestamp BIGINT,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP
);

-- Create whatsapp_sent_messages table
CREATE TABLE IF NOT EXISTS whatsapp_sent_messages (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    phone VARCHAR(20),
    message_text TEXT,
    api_status INT,
    api_response JSONB,
    sent_at TIMESTAMP
);

-- Create whatsapp_send_errors table
CREATE TABLE IF NOT EXISTS whatsapp_send_errors (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    phone VARCHAR(20),
    message_text TEXT,
    error TEXT,
    error_timestamp TIMESTAMP
);

-- Add columns to messages table (SAFE Alter)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'messages' AND column_name = 'source_pipeline') THEN
        ALTER TABLE messages ADD COLUMN source_pipeline VARCHAR DEFAULT 'CHAT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'messages' AND column_name = 'whatsapp_from_phone') THEN
        ALTER TABLE messages ADD COLUMN whatsapp_from_phone VARCHAR;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'messages' AND column_name = 'whatsapp_message_id') THEN
        ALTER TABLE messages ADD COLUMN whatsapp_message_id VARCHAR;
    END IF;
END $$;

-- Add columns to chat_history table (SAFE Alter - assuming it exists or is same as messages? Often chat_history is view or alias, checking if table exists first)
DO $$
BEGIN
    -- Check if chat_history table exists distinct from messages
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_history') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chat_history' AND column_name = 'source_pipeline') THEN
            ALTER TABLE chat_history ADD COLUMN source_pipeline VARCHAR DEFAULT 'CHAT';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chat_history' AND column_name = 'whatsapp_from_phone') THEN
            ALTER TABLE chat_history ADD COLUMN whatsapp_from_phone VARCHAR;
        END IF;
    END IF;
END $$;
