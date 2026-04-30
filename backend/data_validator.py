from jsonschema import SchemaError, ValidationError, validate


def validate_data(data: dict, schema: dict):
    effective_schema = schema.get('items', schema) if schema.get('type') == 'array' else schema
    try:
        validate(instance=data, schema=effective_schema)
        print("Validation passed — data matches the schema.")
        return True, None
    except SchemaError as e:
        print(f"Invalid schema: {e.message}")
        return False, f"Invalid schema: {e.message}"
    except ValidationError as e:
        path = " -> ".join(str(p) for p in e.absolute_path) or "(root)"
        print("Validation failed")
        print(f"Location : {path}")
        print(f"Problem  : {e.message}")
        return False, f"Validation failed at {path}: {e.message}"