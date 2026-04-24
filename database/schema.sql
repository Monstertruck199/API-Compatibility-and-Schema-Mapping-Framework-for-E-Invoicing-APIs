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

CREATE TABLE IF NOT EXISTS transform_runs (
    id SERIAL PRIMARY KEY,
    source_api_id INTEGER REFERENCES apis(id) ON DELETE SET NULL,
    target_api_id INTEGER REFERENCES apis(id) ON DELETE SET NULL,
    source_schema_id INTEGER REFERENCES schemas(id) ON DELETE SET NULL,
    target_schema_id INTEGER REFERENCES schemas(id) ON DELETE SET NULL,
    input_data JSONB NOT NULL,
    output_data JSONB,
    output_text TEXT,
    output_format VARCHAR(20) NOT NULL CHECK (output_format IN ('json', 'xml')),
    mapping_status VARCHAR(50),
    warnings JSONB DEFAULT '[]'::jsonb,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transform_runs_source_api ON transform_runs(source_api_id);
CREATE INDEX IF NOT EXISTS idx_transform_runs_target_api ON transform_runs(target_api_id);
CREATE INDEX IF NOT EXISTS idx_transform_runs_created_at ON transform_runs(created_at DESC);

CREATE OR REPLACE FUNCTION sync_serial_sequence_after_delete()
RETURNS TRIGGER AS $$
DECLARE
    seq_name TEXT;
    max_id BIGINT;
BEGIN
    SELECT pg_get_serial_sequence(format('%I.%I', TG_TABLE_SCHEMA, TG_TABLE_NAME), 'id')
    INTO seq_name;

    IF seq_name IS NULL THEN
        RETURN NULL;
    END IF;

    EXECUTE format('SELECT COALESCE(MAX(id), 0) FROM %I.%I', TG_TABLE_SCHEMA, TG_TABLE_NAME)
    INTO max_id;

    IF max_id = 0 THEN
        PERFORM setval(seq_name::regclass, 1, false);
    ELSE
        PERFORM setval(seq_name::regclass, max_id, true);
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS apis_reset_id_seq_after_delete ON apis;
CREATE TRIGGER apis_reset_id_seq_after_delete
AFTER DELETE ON apis
FOR EACH STATEMENT EXECUTE FUNCTION sync_serial_sequence_after_delete();

DROP TRIGGER IF EXISTS schemas_reset_id_seq_after_delete ON schemas;
CREATE TRIGGER schemas_reset_id_seq_after_delete
AFTER DELETE ON schemas
FOR EACH STATEMENT EXECUTE FUNCTION sync_serial_sequence_after_delete();

DROP TRIGGER IF EXISTS schema_fields_reset_id_seq_after_delete ON schema_fields;
CREATE TRIGGER schema_fields_reset_id_seq_after_delete
AFTER DELETE ON schema_fields
FOR EACH STATEMENT EXECUTE FUNCTION sync_serial_sequence_after_delete();

DROP TRIGGER IF EXISTS compatibility_results_reset_id_seq_after_delete ON compatibility_results;
CREATE TRIGGER compatibility_results_reset_id_seq_after_delete
AFTER DELETE ON compatibility_results
FOR EACH STATEMENT EXECUTE FUNCTION sync_serial_sequence_after_delete();

DROP TRIGGER IF EXISTS compatibility_issues_reset_id_seq_after_delete ON compatibility_issues;
CREATE TRIGGER compatibility_issues_reset_id_seq_after_delete
AFTER DELETE ON compatibility_issues
FOR EACH STATEMENT EXECUTE FUNCTION sync_serial_sequence_after_delete();

DROP TRIGGER IF EXISTS mapping_rules_reset_id_seq_after_delete ON mapping_rules;
CREATE TRIGGER mapping_rules_reset_id_seq_after_delete
AFTER DELETE ON mapping_rules
FOR EACH STATEMENT EXECUTE FUNCTION sync_serial_sequence_after_delete();

DROP TRIGGER IF EXISTS transform_runs_reset_id_seq_after_delete ON transform_runs;
CREATE TRIGGER transform_runs_reset_id_seq_after_delete
AFTER DELETE ON transform_runs
FOR EACH STATEMENT EXECUTE FUNCTION sync_serial_sequence_after_delete();