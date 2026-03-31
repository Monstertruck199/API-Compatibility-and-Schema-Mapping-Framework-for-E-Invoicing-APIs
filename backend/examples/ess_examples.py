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