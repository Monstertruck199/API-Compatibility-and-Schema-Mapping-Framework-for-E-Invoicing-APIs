CREATE TABLE IF NOT EXISTS apis (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('transform', 'validation', 'comms')),
    auth_method VARCHAR(100),
    input_format VARCHAR(100),
    output_format VARCHAR(100),
    base_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS schema_fields (
    id SERIAL PRIMARY KEY,
    api_id INTEGER REFERENCES apis(id) ON DELETE CASCADE,
    field_name VARCHAR(255) NOT NULL,
    field_type VARCHAR(255) NOT NULL,
    is_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS compatibility_results (
    id SERIAL PRIMARY KEY,
    source_api_id INTEGER REFERENCES apis(id) ON DELETE CASCADE,
    target_api_id INTEGER REFERENCES apis(id) ON DELETE CASCADE,
    level VARCHAR(50) NOT NULL CHECK (level IN ('direct', 'mapping', 'incompatible')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS compatibility_issues (
    id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES compatibility_results(id) ON DELETE CASCADE,
    issue_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mapping_rules (
    id SERIAL PRIMARY KEY,
    source_api_id INTEGER REFERENCES apis(id) ON DELETE CASCADE,
    target_api_id INTEGER REFERENCES apis(id) ON DELETE CASCADE,
    source_field VARCHAR(255) NOT NULL,
    target_field VARCHAR(255) NOT NULL,
    transformation_type VARCHAR(100)
);