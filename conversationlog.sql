CREATE TABLE conversation_logs (
    id SERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL,
    tokens_used INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
