VALIDATION_SCHEMA = {
    "type": "object",
    "required": ["id", "type", "event", "rule", "data", "value"],
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["validation"]},
        "event": {
            "type": "object",
            "required": ["time", "actor", "agent", "trigger"],
            "properties": {
                "time": {"type": "string"},
                "actor": {"type": "string"},
                "agent": {"type": "string"},
                "trigger": {"type": "string"},
            },
        },
        "rule": {
            "type": "object",
            "required": ["language", "expression", "severity", "change", "description"],
            "properties": {
                "language": {"type": "string"},
                "expression": {"type": "string"},
                "severity": {"type": "string", "enum": ["error", "warning", "information"]},
                "change": {"type": "string", "enum": ["up", "down"]},
                "description": {"type": "string"},
            },
        },
        "data": {
            "type": "object",
            "required": ["source", "target", "description"],
            "properties": {
                "source": {"type": "array", "items": {"type": "string"}},
                "target": {"type": "array", "items": {"type": "string"}},
                "description": {"type": "string"},
            },
        },
        "value": {"type": "string", "enum": ["0", "1", "NA"]},
    },
}

VALIDATION_SCHEMA_V2 = {
    "type": "object",
    "required": ["id", "kind", "metadata", "policy", "payload", "result"],
    "properties": {
        "id": {"type": "string"},
        "kind": {"type": "string", "enum": ["validation"]},
        "metadata": {
            "type": "object",
            "required": ["timestamp", "user", "service", "source"],
            "properties": {
                "timestamp": {"type": "string"},
                "user": {"type": "string"},
                "service": {"type": "string"},
                "source": {"type": "string"}
            }
        },
        "policy": {
            "type": "object",
            "required": ["lang", "expr", "level", "direction", "summary"],
            "properties": {
                "lang": {"type": "string"},
                "expr": {"type": "string"},
                "level": {"type": "string", "enum": ["error", "warning", "information"]},
                "direction": {"type": "string", "enum": ["up", "down"]},
                "summary": {"type": "string"}
            }
        },
        "payload": {
            "type": "object",
            "required": ["inputs", "outputs", "summary"],
            "properties": {
                "inputs": {"type": "array", "items": {"type": "string"}},
                "outputs": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"}
            }
        },
        "result": {"type": "string", "enum": ["0", "1","NA"]}
    }
}

AGGREGATION_SCHEMA = {
    "type": "object",
    "required": ["id", "type", "event", "aggregate", "data", "value"],
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["aggregation"]},
        "event": {
            "type": "object",
            "required": ["time", "actor", "agent", "trigger"],
            "properties": {
                "time": {"type": "string"},
                "actor": {"type": "string"},
                "agent": {"type": "string"},
                "trigger": {"type": "string"},
            },
        },
        "aggregate": {
            "type": "object",
            "required": ["language", "expression", "description"],
            "properties": {
                "language": {"type": "string"},
                "expression": {"type": "string"},
                "description": {"type": "string"},
            },
        },
        "data": {
            "type": "object",
            "required": ["source", "target", "description"],
            "properties": {
                "source": {"type": "array", "items": {"type": "string"}},
                "target": {"type": "array", "items": {"type": "string"}},
                "description": {"type": "string"},
            },
        },
        "value": {"type": "string"},
    },
}

# One liners (for Python interpreter)

VALIDATION_SCHEMA_ONE_LINE = {"type": "object", "required": ["id", "type", "event", "rule", "data", "value"], "properties": {"id": {"type": "string"}, "type": {"type": "string", "enum": ["validation"]}, "event": {"type": "object", "required": ["time", "actor", "agent", "trigger"], "properties": {"time": {"type": "string"}, "actor": {"type": "string"}, "agent": {"type": "string"}, "trigger": {"type": "string"}}}, "rule": {"type": "object", "required": ["language", "expression", "severity", "change", "description"], "properties": {"language": {"type": "string"}, "expression": {"type": "string"}, "severity": {"type": "string", "enum": ["error", "warning", "information"]}, "change": {"type": "string", "enum": ["up", "down"]}, "description": {"type": "string"}}}, "data": {"type": "object", "required": ["source", "target", "description"], "properties": {"source": {"type": "array", "items": {"type": "string"}}, "target": {"type": "array", "items": {"type": "string"}}, "description": {"type": "string"}}}, "value": {"type": "string", "enum": ["0", "1", "NA"]}}}

AGGREGATION_SCHEMA_ONE_LINE = {"type": "object", "required": ["id", "type", "event", "aggregate", "data", "value"], "properties": {"id": {"type": "string"}, "type": {"type": "string", "enum": ["aggregation"]}, "event": {"type": "object", "required": ["time", "actor", "agent", "trigger"], "properties": {"time": {"type": "string"}, "actor": {"type": "string"}, "agent": {"type": "string"}, "trigger": {"type": "string"}}}, "aggregate": {"type": "object", "required": ["language", "expression", "description"], "properties": {"language": {"type": "string"}, "expression": {"type": "string"}, "description": {"type": "string"}}}, "data": {"type": "object", "required": ["source", "target", "description"], "properties": {"source": {"type": "array", "items": {"type": "string"}}, "target": {"type": "array", "items": {"type": "string"}}, "description": {"type": "string"}}}, "value": {"type": "string"}}}

SOURCE_ONE_LINE = {"type": "object", "required": ["full_name", "dob", "email_address"], "properties": {"full_name": {"type": "string"}, "dob": {"type": "string"}, "email_address": {"type": "string"}}}

TARGET_ONE_LINE = {"type": "object", "required": ["name", "date_of_birth", "email"], "properties": {"name": {"type": "string"}, "date_of_birth": {"type": "string"}, "email": {"type": "string"}}}

SOURCE_NO_REQUIRED_FIELDS_ONE_LINE = {"type": "object", "required": [], "properties": {"full_name": {"type": "string"}, "dob": {"type": "string"}, "email_address": {"type": "string"}}}

TARGET_NO_REQUIRED_FIELDS_ONE_LINE = {"type": "object", "required": [], "properties": {"name": {"type": "string"}, "date_of_birth": {"type": "string"}, "email": {"type": "string"}}}