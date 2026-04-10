CREATE TABLE IF NOT EXISTS apis (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL CHECK (category IN ('transformation', 'validation', 'communication')),
    description TEXT,
    base_url VARCHAR(512),
    auth_method VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS schemas (
    id SERIAL PRIMARY KEY,
    api_id INTEGER NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('input', 'output')),
    format VARCHAR(20) NOT NULL CHECK (format IN ('json', 'xml')),
    raw_schema JSONB NOT NULL,
    normalized_schema JSONB,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (api_id, direction, version)
);

CREATE TABLE IF NOT EXISTS schema_fields (
    id SERIAL PRIMARY KEY,
    schema_id INTEGER NOT NULL REFERENCES schemas(id) ON DELETE CASCADE,
    field_path VARCHAR(512) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    field_type VARCHAR(100) NOT NULL,
    is_required BOOLEAN DEFAULT FALSE,
    nesting_depth INTEGER DEFAULT 0,
    parent_path VARCHAR(512),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schema_fields_schema_id ON schema_fields(schema_id);
CREATE INDEX IF NOT EXISTS idx_schema_fields_field_path ON schema_fields(field_path);

CREATE TABLE IF NOT EXISTS compatibility_results (
    id SERIAL PRIMARY KEY,
    source_api_id INTEGER NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    target_api_id INTEGER NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    source_schema_id INTEGER REFERENCES schemas(id) ON DELETE SET NULL,
    target_schema_id INTEGER REFERENCES schemas(id) ON DELETE SET NULL,
    compatibility_level VARCHAR(50) NOT NULL CHECK (compatibility_level IN ('directly_compatible', 'compatible_with_mapping', 'incompatible')),
    summary JSONB,
    full_result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (source_schema_id, target_schema_id)
);

CREATE INDEX IF NOT EXISTS idx_compat_source ON compatibility_results(source_api_id);
CREATE INDEX IF NOT EXISTS idx_compat_target ON compatibility_results(target_api_id);

CREATE TABLE IF NOT EXISTS compatibility_issues (
    id SERIAL PRIMARY KEY,
    result_id INTEGER NOT NULL REFERENCES compatibility_results(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL,
    kind VARCHAR(20) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    source_path VARCHAR(512),
    target_path VARCHAR(512),
    message TEXT NOT NULL,
    suggestion TEXT
);

CREATE INDEX IF NOT EXISTS idx_issues_result ON compatibility_issues(result_id);

CREATE TABLE IF NOT EXISTS mapping_rules (
    id SERIAL PRIMARY KEY,
    source_api_id INTEGER NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    target_api_id INTEGER NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    source_field VARCHAR(512) NOT NULL,
    target_field VARCHAR(512) NOT NULL,
    transform_type VARCHAR(50) NOT NULL DEFAULT 'rename',
    source_type VARCHAR(50),
    target_type VARCHAR(50),
    confidence VARCHAR(20) DEFAULT 'high',
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mapping_source ON mapping_rules(source_api_id);
CREATE INDEX IF NOT EXISTS idx_mapping_target ON mapping_rules(target_api_id);