CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_name VARCHAR(200),
    dob DATE,
    member_id VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    claim_number VARCHAR(100),
    claim_status VARCHAR(100),
    claim_type VARCHAR(100),
    claim_date DATE,
    adjudication_status VARCHAR(100),
    total_amount DECIMAL(18,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR(50) PRIMARY KEY,
    claim_id VARCHAR(50),
    customer_id VARCHAR(50),
    case_status VARCHAR(100),
    case_type VARCHAR(100),
    assigned_agent_id VARCHAR(50),
    priority VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    source_system VARCHAR(100),
    interaction_type VARCHAR(100),
    interaction_timestamp TIMESTAMP,
    call_duration_seconds INT,
    call_reason VARCHAR(200),
    agent_id VARCHAR(50),
    outcome VARCHAR(100),
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS vendor_policies (
    policy_id VARCHAR(50) PRIMARY KEY,
    vendor_name VARCHAR(150),
    policy_category VARCHAR(100),
    policy_title VARCHAR(200),
    policy_text TEXT,
    effective_date DATE,
    version_no VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS ppw_records (
    ppw_id VARCHAR(50) PRIMARY KEY,
    claim_id VARCHAR(50),
    customer_id VARCHAR(50),
    medical_record_id VARCHAR(100),
    ppw_status VARCHAR(100),
    ppw_received_date DATE,
    ppw_review_status VARCHAR(100),
    notes TEXT,
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS submissions (
    submission_id VARCHAR(50) PRIMARY KEY,
    claim_id VARCHAR(50),
    customer_id VARCHAR(50),
    submission_status VARCHAR(100),
    submitted_at TIMESTAMP,
    document_count INT,
    error_code VARCHAR(100),
    rejection_reason TEXT,
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS ingestion_watermarks (
    source_name VARCHAR(100) PRIMARY KEY,
    last_watermark TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_errors (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100),
    target_table VARCHAR(100),
    error_type VARCHAR(100),
    error_message TEXT,
    raw_payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
