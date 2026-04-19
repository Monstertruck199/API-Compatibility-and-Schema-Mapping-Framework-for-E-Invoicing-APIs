from jsonschema import validate, ValidationError, SchemaError
 
def validate_data(data: dict, schema: dict):
    try:
        validate(instance=data, schema=schema)
        print("Validation passed — data matches the schema.")
        return True
    except SchemaError as e:
        print(f"Invalid schema: {e.message}")
        return False
    except ValidationError as e:
        path = " -> ".join(str(p) for p in e.absolute_path) or "(root)"
        print(f"Validation failed")
        print(f"Location : {path}")
        print(f"Problem  : {e.message}")
        return False